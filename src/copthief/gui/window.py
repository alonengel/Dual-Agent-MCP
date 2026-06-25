"""A live graphical window that redraws the board after every turn.

This is the real-time interface: it plugs into ``MatchRunner.board_render`` (the
same per-turn hook the ASCII board uses) and updates an interactive matplotlib
figure as the game unfolds, so the agents are seen moving while they play.

It is intentionally best-effort: on a headless machine (no interactive backend)
construction fails gracefully and the call becomes a no-op, so a ``--animate``
run never crashes a CI box or a display-less server.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from copthief.domain.subgame import Subgame


class LiveWindow:
    """Callable per-turn board renderer backed by an interactive matplotlib figure."""

    def __init__(self, pause: float = 0.6):
        self.pause = pause
        self._ok = False
        self._fig = None
        self._ax = None
        try:  # interactive backend may be absent (headless) — degrade silently
            import matplotlib.pyplot as plt

            from copthief.gui.board_draw import legend_handles

            plt.ion()
            self._plt = plt
            self._fig, self._ax = plt.subplots(figsize=(4.2, 4.2))
            self._fig.legend(handles=legend_handles(), loc="upper center", ncol=3, fontsize=8)
            self._fig.canvas.manager.set_window_title("CopThief — live")
            self._ok = True
        except Exception:
            self._ok = False

    def __call__(self, game: Subgame) -> str:
        """Redraw the board for the current turn; returns "" so nothing extra prints."""
        if not self._ok:
            return ""
        from copthief.gui.board_draw import draw_board

        board = game.board
        self._ax.clear()
        draw_board(self._ax, board.width, board.height, board.origin,
                   game.cop.as_tuple(), game.thief.as_tuple(), board.barriers,
                   title=f"move {game.move_number} · {game.turn.value} to act")
        try:
            self._fig.canvas.draw_idle()
            self._plt.pause(self.pause)
        except Exception:
            self._ok = False
        return ""

    def close(self) -> None:
        """Leave the final frame on screen until the user dismisses the window."""
        if not self._ok:
            return
        with contextlib.suppress(Exception):
            self._plt.ioff()
            self._plt.show()
