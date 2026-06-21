"""Render a per-move board filmstrip from the audit log for demo screenshots."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless image rendering
import matplotlib.pyplot as plt  # noqa: E402


def _turns_for_subgame(audit_path: Path, index: int | None) -> list[dict]:
    """Return the 'turn' entries for one subgame (the last one if index is None)."""
    entries = [json.loads(x) for x in audit_path.read_text(encoding="utf-8").splitlines()]
    turns = [e for e in entries if e.get("event") == "turn"]
    if not turns:
        return []
    target = index if index is not None else max(t["index"] for t in turns)
    return [t for t in turns if t["index"] == target]


def _draw(ax, turn: dict, span: int, barriers: set[tuple[int, int]]) -> None:
    """Draw one board frame: grid, barriers, cop and thief markers."""
    ax.set_xticks(range(1, span + 1))
    ax.set_yticks(range(1, span + 1))
    ax.set_xlim(0.5, span + 0.5)
    ax.set_ylim(0.5, span + 0.5)
    ax.grid(True)
    ax.set_aspect("equal")
    for bx, by in barriers:
        ax.scatter(bx, by, s=260, c="dimgray", marker="s")
    ax.scatter(*turn["cop"], s=240, c="tab:blue", marker="s", label="Cop")
    ax.scatter(*turn["thief"], s=240, c="tab:red", marker="o", label="Thief")
    ax.set_title(f"move {turn['move']} ({turn['role']})", fontsize=8)


def render_frames(audit_path: Path, root: Path, index: int | None = None) -> Path | None:
    """Render a montage of every move in one subgame; return the montage path."""
    turns = _turns_for_subgame(audit_path, index)
    if not turns:
        return None
    span = max(max(t["cop"][0], t["cop"][1], t["thief"][0], t["thief"][1]) for t in turns)
    span = max(span, 5)

    cols = 5
    rows = (len(turns) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(3 * cols, 3 * rows), squeeze=False)
    barriers: set[tuple[int, int]] = set()
    for n, turn in enumerate(turns):
        if turn.get("action") == "block":
            barriers.add(tuple(turn["cop"]))
        _draw(axes[n // cols][n % cols], turn, span, barriers)
    for n in range(len(turns), rows * cols):
        axes[n // cols][n % cols].axis("off")

    out_dir = root / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "demo_filmstrip.png"
    fig.suptitle(f"CopThief subgame {turns[0]['index']} — move-by-move", fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return out_path
