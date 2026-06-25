"""Animated board playback from the audit log.

Turns the recorded game into a moving picture: a matplotlib animation that steps
through every move so the cop, thief and barriers are seen *moving* across the
board. Two outputs from the same frames:

* an interactive window (``show=True``) — the real-time graphical interface;
* a saved ``.gif`` (``save_gif=True``) — a headless, CI-friendly proof artifact
  that is strictly stronger than a static screenshot.
"""

from __future__ import annotations

import contextlib
import json
import textwrap
from pathlib import Path

from copthief.gui.board_draw import SPEAKER_COLOUR, draw_board, legend_handles

# NB: matplotlib.pyplot is imported lazily inside the functions so importing this
# module never locks a backend. Callers that need headless output (capture_demo,
# tests) select "Agg" first; the interactive `replay` window keeps the default.


def _frames(audit_path: Path) -> list[dict]:
    """Flatten the audit log into per-move frames with cumulative barriers.

    Each subgame opens with a ``start`` frame taken from the ``subgame_start``
    event — the *true* initial layout, before anyone has moved — so the very
    first thing the viewer sees is the real starting position rather than the
    board after the thief's opening step. Subsequent frames are the post-move
    boards recorded by each ``turn`` event (hence labelled "moved", past tense).
    Barriers reset at every subgame boundary; a frame inherits all barriers the
    cop has dropped so far within the current subgame.
    """
    if not audit_path.exists():
        return []
    entries = [json.loads(x) for x in audit_path.read_text(encoding="utf-8").splitlines()]
    frames: list[dict] = []
    barriers: set[tuple[int, int]] = set()
    current_index: int | None = None
    for entry in entries:
        event = entry.get("event")
        if event == "subgame_start":
            current_index, barriers = entry["index"], set()
            frames.append({
                "index": entry["index"], "move": 0, "role": "start",
                "cop": tuple(entry["cop"]), "thief": tuple(entry["thief"]),
                "barriers": set(), "message": "",
            })
            continue
        if event != "turn":
            continue
        if entry["index"] != current_index:
            current_index, barriers = entry["index"], set()
        if entry.get("action") == "block":
            barriers.add(tuple(entry["cop"]))
        frames.append({
            "index": entry["index"], "move": entry["move"], "role": entry["role"],
            "cop": tuple(entry["cop"]), "thief": tuple(entry["thief"]),
            "barriers": set(barriers), "message": entry.get("message", ""),
        })
    return frames


def _grid() -> tuple[int, int, int]:
    """Read the configured board width, height and origin (full/hardest board)."""
    from copthief.shared.config import Config

    game = Config.load().section("game")
    width, height = game.get("grid_size", [5, 5])
    return int(width), int(height), int(game.get("origin", 1))


def _caption(ax, frame: dict) -> None:
    """Render the turn's free-language taunt below the board, coloured by speaker."""
    message = frame.get("message", "")
    if not message:
        return
    text = message if len(message) <= 160 else message[:157] + "…"
    wrapped = textwrap.fill(f'{frame["role"]}: "{text}"', width=50)
    ax.set_xlabel(wrapped, fontsize=7, style="italic",
                  color=SPEAKER_COLOUR.get(frame["role"], "0.2"))


def build_animation(audit_path: Path, interval: int = 700) -> tuple | None:
    """Build (figure, FuncAnimation) for the recorded game, or None if no frames."""
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    frames = _frames(audit_path)
    if not frames:
        return None
    width, height, origin = _grid()
    fig, ax = plt.subplots(figsize=(4.6, 5.4))
    fig.legend(handles=legend_handles(), loc="upper center", ncol=3, fontsize=8)
    fig.subplots_adjust(top=0.86, bottom=0.30)  # leave room for the dialogue caption

    def _render(frame: dict) -> None:
        ax.clear()
        if frame["role"] == "start":
            title = f"Subgame {frame['index']} · start"
        else:
            title = (f"Subgame {frame['index']} · move {frame['move']} · "
                     f"{frame['role']} moved")
        draw_board(ax, width, height, origin, frame["cop"], frame["thief"],
                   frame["barriers"], title=title)
        _caption(ax, frame)

    anim = FuncAnimation(fig, _render, frames=frames, interval=interval,
                         blit=False, repeat=False)
    return fig, anim


def animate_audit(audit_path: Path, root: Path, *, save_gif: bool = False,
                  gif_name: str = "demo_animation.gif", show: bool = True,
                  interval: int = 700) -> Path | None:
    """Animate the recorded game; optionally save a GIF and/or open a window.

    Returns the GIF path when one was written, else None.
    """
    import matplotlib.pyplot as plt
    from matplotlib.animation import PillowWriter

    built = build_animation(audit_path, interval=interval)
    if built is None:
        return None
    fig, anim = built
    out_path: Path | None = None
    if save_gif:
        out_dir = root / "assets"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / gif_name
        anim.save(out_path, writer=PillowWriter(fps=max(1, round(1000 / interval))))
    if show:
        # Headless / no interactive backend: no-op; the GIF is still produced.
        with contextlib.suppress(Exception):
            plt.show()
    plt.close(fig)
    return out_path
