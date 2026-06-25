"""A live graphical window that redraws the board after every turn.

This is the real-time interface: it plugs into ``MatchRunner.board_render`` (the
same per-turn hook the ASCII board uses) and updates an interactive matplotlib
figure as the game unfolds, so the agents are seen moving while they play. A
side panel shows the running dialogue log (the taunts), so the whole game —
movement *and* free-language messages — is visible in the GUI itself, no terminal
needed.

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
    """Callable per-turn renderer: an interactive board plus a live dialogue log."""

    def __init__(self, pause: float = 0.6, max_log: int = 12):
        self.pause = pause
        self.max_log = max_log
        self._log: list[tuple[str, str]] = []  # (speaker, message) history
        self._ok = False
        self._fig = self._board = self._panel = None
        try:  # interactive backend may be absent (headless) — degrade silently
            import matplotlib.pyplot as plt

            from copthief.gui.board_draw import legend_handles

            plt.ion()
            self._plt = plt
            self._fig, (self._board, self._panel) = plt.subplots(
                1, 2, figsize=(8.4, 4.8), gridspec_kw={"width_ratios": [1.05, 1]})
            self._fig.legend(handles=legend_handles(), loc="upper left", ncol=3, fontsize=8)
            self._fig.subplots_adjust(top=0.86, wspace=0.1)
            self._fig.canvas.manager.set_window_title("CopThief — live")
            self._ok = True
        except Exception:
            self._ok = False

    def __call__(self, game: Subgame, message: str = "") -> str:
        """Redraw the board and append the latest taunt to the dialogue log; returns "".

        The mover is the agent that just acted — the *other* role is now to act — so the
        message is attributed to the speaker that produced it.
        """
        if not self._ok:
            return ""
        from copthief.gui.board_draw import draw_board, draw_log

        board = game.board
        speaker = "cop" if game.turn.value == "thief" else "thief"  # turn already advanced
        if message:
            self._log.append((speaker, message))
        self._board.clear()
        draw_board(self._board, board.width, board.height, board.origin,
                   game.cop.as_tuple(), game.thief.as_tuple(), board.barriers,
                   title=f"move {game.move_number} · {game.turn.value} to act")
        self._panel.clear()
        draw_log(self._panel, self._log, max_lines=self.max_log)
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
