"""Tests for move legality rules."""

from __future__ import annotations

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Position
from copthief.domain.rules import validate


def test_single_step_move_is_legal(board: Board) -> None:
    move = Move(Role.THIEF, Action.MOVE, 1, 1)
    result = validate(move, Position(1, 1), board, barriers_left=0)
    assert result.legal
    assert result.new_pos == Position(2, 2)


def test_two_step_move_rejected(board: Board) -> None:
    move = Move(Role.THIEF, Action.MOVE, 2, 0)
    assert not validate(move, Position(1, 1), board, 0).legal


def test_move_off_board_rejected(board: Board) -> None:
    move = Move(Role.COP, Action.MOVE, -1, 0)
    assert not validate(move, Position(1, 1), board, 0).legal


def test_diagonal_rejected_when_disabled() -> None:
    board = Board(5, 5, origin=1, diagonal=False)
    move = Move(Role.COP, Action.MOVE, 1, 1)
    assert not validate(move, Position(2, 2), board, 0).legal


def test_only_cop_places_barrier(board: Board) -> None:
    thief_block = Move(Role.THIEF, Action.BLOCK)
    assert not validate(thief_block, Position(1, 1), board, 5).legal
    cop_block = Move(Role.COP, Action.BLOCK)
    assert validate(cop_block, Position(1, 1), board, 5).legal


def test_barrier_requires_remaining_quota(board: Board) -> None:
    cop_block = Move(Role.COP, Action.BLOCK)
    assert not validate(cop_block, Position(1, 1), board, 0).legal


def test_entering_barrier_is_illegal(board: Board) -> None:
    board.add_barrier(Position(2, 1))
    move = Move(Role.THIEF, Action.MOVE, 1, 0)
    assert not validate(move, Position(1, 1), board, 0).legal
