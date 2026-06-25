"""Shared board rendering: a grid of cells with agents drawn INSIDE the cells.

Grid lines are placed at half-integer cell boundaries and the integer coordinates
are cell centres, so the cop/thief/barriers render inside the blocks (not on lines).
"""

from __future__ import annotations

import textwrap

# NB: this module is backend-neutral on purpose. Headless PNG generators
# (viewer.py, sequence.py) select the "Agg" backend themselves; the animated
# window (animate.py / window.py) needs an interactive backend instead.
from matplotlib.patches import Circle, Rectangle

# Per-speaker colours, shared by the live window and the GIF dialogue captions/log.
SPEAKER_COLOUR = {"cop": "tab:blue", "thief": "tab:red"}


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


def draw_log(ax, entries, max_lines: int = 12) -> None:
    """Render a scrolling dialogue panel: recent taunts, newest last, coloured by speaker.

    ``entries`` is a list of ``(speaker, message)`` tuples; only the last few are shown so the
    panel reads like a chat log next to the board.
    """
    ax.axis("off")
    ax.set_title("dialogue", fontsize=9, loc="left")
    y = 0.99
    for speaker, message in entries[-max_lines:]:
        wrapped = textwrap.fill(f'{speaker}: "{message}"', width=38, subsequent_indent="   ")
        ax.text(0.0, y, wrapped, transform=ax.transAxes, fontsize=6.5, va="top",
                color=SPEAKER_COLOUR.get(speaker, "0.2"))
        y -= 0.045 * (wrapped.count("\n") + 1) + 0.015
        if y < 0.03:
            break
