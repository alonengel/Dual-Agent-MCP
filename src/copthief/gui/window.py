"""A live graphical window that redraws the board after every turn.

This is the real-time interface: an interactive matplotlib figure (board + a running
dialogue log) updated as the game unfolds, so the agents are seen moving and talking
while they play — no terminal needed.

**Responsiveness:** moves may involve slow (real-LLM) turns, and Tk's event loop must run
on the main thread. So the match runs on a **worker thread** that only *enqueues* lightweight
board snapshots, while this object *consumes* them and draws on the main thread, pumping the
event loop between frames. The window therefore stays responsive even while a turn blocks for
seconds on the model (no more "Not Responding").

Best-effort: on a headless machine construction fails gracefully and the match still runs
without a window, so ``--animate`` never crashes a display-less box.
"""

from __future__ import annotations

import contextlib
import queue
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from copthief.domain.subgame import Subgame

_DONE = object()  # sentinel pushed onto the queue when the match stops producing frames


class LiveWindow:
    """Threaded live view: board + dialogue log, driven by a background match thread."""

    def __init__(self, pause: float = 0.6, max_log: int = 12):
        self.pause = pause
        self.max_log = max_log
        self._log: list[tuple[str, str]] = []
        self._queue: queue.Queue = queue.Queue()
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

    def enqueue(self, game: Subgame, message: str = "") -> str:
        """Board-render hook (worker thread): snapshot the turn for the GUI to draw. Returns ""."""
        board = game.board
        speaker = "cop" if game.turn.value == "thief" else "thief"  # turn already advanced
        self._queue.put({
            "w": board.width, "h": board.height, "o": board.origin,
            "cop": game.cop.as_tuple(), "thief": game.thief.as_tuple(),
            "barriers": set(board.barriers), "move": game.move_number,
            "turn": game.turn.value, "speaker": speaker, "message": message,
        })
        return ""

    def run_match(self, sdk: Any, games: int | None, reporter: Any) -> dict:
        """Run the match on a worker thread while pumping the GUI here; return the result."""
        if not self._ok:  # headless: just play the match, no window
            return sdk.run_self_play(games=games, reporter=reporter)
        holder: dict[str, Any] = {}

        def worker() -> None:
            try:
                holder["match"] = sdk.run_self_play(
                    games=games, reporter=reporter, board_render=self.enqueue)
            except BaseException as exc:  # surface worker failures on the main thread
                holder["error"] = exc
            finally:
                self._queue.put(_DONE)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        self._consume()
        thread.join()
        if "error" in holder:
            raise holder["error"]
        return holder.get("match", {"totals": {}, "sub_games": []})

    def _consume(self) -> None:
        """Main-thread loop: draw queued frames, pumping the event loop until the _DONE sentinel."""
        while True:
            try:
                frame = self._queue.get_nowait()
            except queue.Empty:
                self._plt.pause(0.05)  # idle: keep the window responsive during slow turns
                continue
            if frame is _DONE:
                return
            self._draw(frame)
            self._plt.pause(self.pause)

    def _draw(self, frame: dict) -> None:
        """Render one snapshot frame: board on the left, accumulated dialogue log on the right."""
        from copthief.gui.board_draw import draw_board, draw_log

        if frame["message"]:
            self._log.append((frame["speaker"], frame["message"]))
        self._board.clear()
        draw_board(self._board, frame["w"], frame["h"], frame["o"],
                   frame["cop"], frame["thief"], frame["barriers"],
                   title=f"move {frame['move']} · {frame['turn']} to act")
        self._panel.clear()
        draw_log(self._panel, self._log, max_lines=self.max_log)

    def close(self) -> None:
        """Leave the final frame on screen until the user dismisses the window."""
        if not self._ok:
            return
        with contextlib.suppress(Exception):
            self._plt.ioff()
            self._plt.show()
