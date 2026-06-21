"""Render the final board state from the audit log into a PNG (proof of play)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from copthief.gui.board_draw import draw_board, legend_handles


def _read_turns(audit_path: Path) -> list[dict]:
    """Load all 'turn' audit entries from the JSON-lines log."""
    if not audit_path.exists():
        return []
    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    return [e for e in entries if e.get("event") == "turn"]


def _grid(root: Path) -> tuple[int, int, int]:
    """Read the configured grid width, height and origin."""
    from copthief.shared.config import Config

    game = Config.load().section("game")
    width, height = game.get("grid_size", [5, 5])
    return int(width), int(height), int(game.get("origin", 1))


def render_audit(audit_path: Path, root: Path, out_name: str = "board.png") -> Path | None:
    """Draw the final recorded board (agents inside cells) and save it to assets/."""
    turns = _read_turns(audit_path)
    if not turns:
        return None
    last = turns[-1]
    sub_turns = [t for t in turns if t["index"] == last["index"]]
    barriers = [tuple(t["cop"]) for t in sub_turns if t.get("action") == "block"]
    width, height, origin = _grid(root)

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    draw_board(ax, width, height, origin, tuple(last["cop"]), tuple(last["thief"]),
               barriers, title=f"CopThief — subgame {last.get('index')} move {last.get('move')}")
    ax.legend(handles=legend_handles(), loc="upper left", bbox_to_anchor=(1.02, 1))

    out_dir = root / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out_path
