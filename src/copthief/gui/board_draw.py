"""Shared board rendering: a grid of cells with agents drawn INSIDE the cells.

Grid lines are placed at half-integer cell boundaries and the integer coordinates
are cell centres, so the cop/thief/barriers render inside the blocks (not on lines).
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless image rendering (set before any figure is created)
from matplotlib.patches import Circle, Rectangle  # noqa: E402


def draw_board(ax, width: int, height: int, origin: int, cop: tuple[int, int],
               thief: tuple[int, int], barriers, title: str = "") -> None:
    """Render one board frame onto ``ax`` with agents centred inside their cells."""
    ax.set_xticks(range(origin, origin + width))
    ax.set_yticks(range(origin, origin + height))
    ax.set_xticks([i - 0.5 for i in range(origin, origin + width + 1)], minor=True)
    ax.set_yticks([i - 0.5 for i in range(origin, origin + height + 1)], minor=True)
    ax.grid(which="minor", color="0.55", linewidth=1)
    ax.tick_params(which="minor", length=0)
    ax.set_xlim(origin - 0.5, origin + width - 0.5)
    ax.set_ylim(origin - 0.5, origin + height - 0.5)
    ax.set_aspect("equal")

    for bx, by in barriers:
        ax.add_patch(Rectangle((bx - 0.5, by - 0.5), 1, 1, facecolor="dimgray"))
    cx, cy = cop
    ax.add_patch(Rectangle((cx - 0.5, cy - 0.5), 1, 1, facecolor="tab:blue", alpha=0.85))
    ax.add_patch(Circle((float(thief[0]), float(thief[1])), 0.32, facecolor="tab:red",
                        zorder=3))
    if title:
        ax.set_title(title, fontsize=8)


def legend_handles():
    """Proxy artists for a board legend (cop / thief / barrier)."""
    return [
        Rectangle((0, 0), 1, 1, facecolor="tab:blue", alpha=0.85, label="Cop"),
        Circle((0, 0), 0.3, facecolor="tab:red", label="Thief"),
        Rectangle((0, 0), 1, 1, facecolor="dimgray", label="Barrier"),
    ]
