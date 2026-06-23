"""Render a per-move board filmstrip from the audit log for demo screenshots."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

from copthief.gui.board_draw import draw_board


def _turns_for_subgame(audit_path: Path, index: int | None) -> list[dict]:
    """Return the 'turn' entries for one subgame (the last one if index is None)."""
    entries = [json.loads(x) for x in audit_path.read_text(encoding="utf-8").splitlines()]
    turns = [e for e in entries if e.get("event") == "turn"]
    if not turns:
        return []
    target = index if index is not None else max(t["index"] for t in turns)
    return [t for t in turns if t["index"] == target]


def _grid(root: Path) -> tuple[int, int, int]:
    """Read the configured grid width, height and origin (full board, hardest mode)."""
    from copthief.shared.config import Config

    game = Config.load().section("game")
    width, height = game.get("grid_size", [5, 5])
    return int(width), int(height), int(game.get("origin", 1))


def render_frames(audit_path: Path, root: Path, index: int | None = None,
                  out_name: str = "demo_filmstrip.png") -> Path | None:
    """Render a montage of every move in one subgame; return the montage path."""
    turns = _turns_for_subgame(audit_path, index)
    if not turns:
        return None
    width, height, origin = _grid(root)

    cols = 5
    rows = (len(turns) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(2.6 * cols, 2.6 * rows), squeeze=False)
    barriers: set[tuple[int, int]] = set()
    for n, turn in enumerate(turns):
        if turn.get("action") == "block":
            barriers.add(tuple(turn["cop"]))
        draw_board(axes[n // cols][n % cols], width, height, origin,
                   tuple(turn["cop"]), tuple(turn["thief"]), barriers,
                   title=f"move {turn['move']} ({turn['role']})")
    for n in range(len(turns), rows * cols):
        axes[n // cols][n % cols].axis("off")

    out_dir = root / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name
    fig.suptitle(f"CopThief subgame {turns[0]['index']} — move-by-move", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return out_path


def _subgame_indices(audit_path: Path) -> list[int]:
    """Return the ordered subgame indices recorded in the audit log."""
    entries = [json.loads(x) for x in audit_path.read_text(encoding="utf-8").splitlines()]
    return sorted({e["index"] for e in entries if e.get("event") == "turn"})


def render_all_subgames(audit_path: Path, root: Path) -> list[Path]:
    """Render one filmstrip per subgame (the whole game each); return the montage paths."""
    paths: list[Path] = []
    for idx in _subgame_indices(audit_path):
        out = render_frames(audit_path, root, index=idx, out_name=f"demo_filmstrip_sg{idx}.png")
        if out is not None:
            paths.append(out)
    return paths
