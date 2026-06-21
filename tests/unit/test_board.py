"""Tests for board geometry, bounds and barriers."""

from __future__ import annotations

import random

from copthief.domain.board import Board
from copthief.domain.models import Position


def test_in_bounds_and_origin(board: Board) -> None:
    assert board.in_bounds(Position(1, 1))
    assert board.in_bounds(Position(5, 5))
    assert not board.in_bounds(Position(0, 1))
    assert not board.in_bounds(Position(6, 5))


def test_barrier_blocks_cell(board: Board) -> None:
    spot = Position(3, 3)
    board.add_barrier(spot)
    assert board.is_barrier(spot)
    assert not board.is_free(spot)


def test_free_neighbours_excludes_blocked(board: Board) -> None:
    here = Position(1, 1)
    board.add_barrier(Position(2, 2))
    neighbours = board.free_neighbours(here)
    assert Position(2, 2) not in neighbours
    assert all(board.in_bounds(n) for n in neighbours)


def test_free_neighbours_cardinal_only() -> None:
    board = Board(5, 5, origin=1, diagonal=False)
    assert len(board.directions()) == 4


def test_random_free_cell_respects_exclude() -> None:
    board = Board(2, 2, origin=1, diagonal=True)
    rng = random.Random(1)
    chosen = board.random_free_cell(rng, exclude={(1, 1), (1, 2), (2, 1)})
    assert chosen == Position(2, 2)
