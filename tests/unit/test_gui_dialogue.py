"""Tests for the GUI dialogue rendering: the shared log panel and the live window's log."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=True)  # headless: never open a window in tests

import matplotlib.pyplot as plt  # noqa: E402

from copthief.constants import Action, Role  # noqa: E402
from copthief.domain.board import Board  # noqa: E402
from copthief.domain.models import Move, Position  # noqa: E402
from copthief.domain.subgame import Subgame  # noqa: E402
from copthief.gui.board_draw import SPEAKER_COLOUR, draw_log  # noqa: E402
from copthief.gui.window import LiveWindow  # noqa: E402


def test_draw_log_renders_recent_entries_coloured_by_speaker() -> None:
    fig, ax = plt.subplots()
    entries = [("thief", "you can't catch me"), ("cop", "closing in"), ("thief", "watch me run")]
    draw_log(ax, entries, max_lines=2)  # only the last two should be shown
    texts = [t.get_text() for t in ax.texts]
    assert any("closing in" in t for t in texts)
    assert any("watch me run" in t for t in texts)
    assert all("you can't catch me" not in t for t in texts)  # trimmed by max_lines
    plt.close(fig)


def test_live_window_accumulates_dialogue_with_correct_speaker() -> None:
    window = LiveWindow()
    if not window._ok:  # no usable backend at all — nothing to assert
        return
    game = Subgame(Board(5, 5, 1, True), Position(4, 5), Position(2, 3), 25, 5)
    game.apply(Move(Role.THIEF, Action.MOVE, 1, 0))  # thief acts; turn advances to cop
    window(game, "you'll never catch me")
    game.apply(Move(Role.COP, Action.MOVE, 0, -1))   # cop acts; turn advances to thief
    window(game, "I'm right behind you")
    assert window._log == [("thief", "you'll never catch me"), ("cop", "I'm right behind you")]


def test_speaker_colours_cover_both_roles() -> None:
    assert SPEAKER_COLOUR["cop"] != SPEAKER_COLOUR["thief"]
