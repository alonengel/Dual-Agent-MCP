"""Render the board state from the audit log into a saved PNG (proof of play)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: write image files without a display server
import matplotlib.pyplot as plt  # noqa: E402


def _read_turns(audit_path: Path) -> list[dict]:
    """Load all 'turn' audit entries from the JSON-lines log."""
    if not audit_path.exists():
        return []
    entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    return [e for e in entries if e.get("event") == "turn"]


def render_audit(audit_path: Path, root: Path, out_name: str = "board.png") -> Path | None:
    """Draw the final recorded position of cop and thief and save it to assets/."""
    turns = _read_turns(audit_path)
    if not turns:
        return None
    last = turns[-1]
    cop, thief = tuple(last["cop"]), tuple(last["thief"])

    fig, ax = plt.subplots(figsize=(5, 5))
    span = max(cop[0], cop[1], thief[0], thief[1], 5) + 1
    ax.set_xticks(range(span + 1))
    ax.set_yticks(range(span + 1))
    ax.grid(True, which="both")
    ax.set_xlim(0, span)
    ax.set_ylim(0, span)
    ax.scatter(*cop, s=400, c="tab:blue", marker="s", label="Cop")
    ax.scatter(*thief, s=400, c="tab:red", marker="o", label="Thief")
    ax.set_title(f"CopThief — subgame {last.get('index')} move {last.get('move')}")
    ax.legend(loc="upper right")

    out_dir = root / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out_path
