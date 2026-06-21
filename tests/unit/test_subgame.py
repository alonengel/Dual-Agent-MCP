"""Tests for the subgame state machine and terminal outcomes."""

from __future__ import annotations

from copthief.constants import Action, Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Position
from copthief.domain.subgame import Subgame


def _game(cop: Position, thief: Position, max_moves: int = 25) -> Subgame:
    return Subgame(Board(5, 5, 1, True), cop, thief, max_moves, 5)


def test_thief_moves_first() -> None:
    game = _game(Position(1, 1), Position(5, 5))
    assert game.turn is Role.THIEF


def test_capture_yields_cop_win() -> None:
    game = _game(Position(2, 1), Position(1, 1))
    game.apply(Move(Role.THIEF, Action.STAY))         # thief stays at (1,1)
    game.apply(Move(Role.COP, Action.MOVE, -1, 0))    # cop steps onto thief
    assert game.captured()
    assert game.outcome is Outcome.COP_WIN


def test_thief_survives_to_move_limit() -> None:
    game = _game(Position(1, 1), Position(5, 5), max_moves=1)
    game.apply(Move(Role.THIEF, Action.STAY))
    game.apply(Move(Role.COP, Action.STAY))
    assert game.outcome is Outcome.THIEF_WIN


def test_move_counter_advances_after_cop() -> None:
    game = _game(Position(1, 1), Position(5, 5))
    game.apply(Move(Role.THIEF, Action.MOVE, 0, -1))
    assert game.move_number == 0
    game.apply(Move(Role.COP, Action.MOVE, 0, 1))
    assert game.move_number == 1


def test_barrier_consumes_quota_and_keeps_position() -> None:
    game = _game(Position(3, 3), Position(5, 5))
    game.apply(Move(Role.THIEF, Action.STAY))
    game.apply(Move(Role.COP, Action.BLOCK))
    assert game.barriers_left == 4
    assert game.cop == Position(3, 3)
    assert game.board.is_barrier(Position(3, 3))


def test_apply_after_finish_raises() -> None:
    game = _game(Position(2, 1), Position(1, 1))
    game.apply(Move(Role.THIEF, Action.STAY))
    game.apply(Move(Role.COP, Action.MOVE, -1, 0))
    try:
        game.apply(Move(Role.THIEF, Action.STAY))
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass
