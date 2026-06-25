"""Tests for the blind-cop patrol geometry (coverage posts vs corner fallback)."""

from __future__ import annotations

from copthief.domain.board import Board
from copthief.domain.models import Position
from copthief.orchestrator import patrol
from copthief.strategy.base import chebyshev


def _covers(posts: list[Position], cell: Position, radius: int) -> bool:
    """True if some post sees ``cell`` within Chebyshev ``radius``."""
    return any(chebyshev(p, cell) <= radius for p in posts)


def _all_cells(board: Board) -> list[Position]:
    return [Position(x, y)
            for x in range(board.origin, board.origin + board.width)
            for y in range(board.origin, board.origin + board.height)]


def test_observation_posts_tile_the_5x5_board() -> None:
    board = Board(5, 5, 1, True)
    route = patrol.patrol_route(board, radius=1)
    assert {p.as_tuple() for p in route} == {(2, 2), (2, 4), (4, 2), (4, 4)}
    # Every cell on the board is seen from at least one post — no blind spot.
    assert all(_covers(route, cell, 1) for cell in _all_cells(board))


def test_corner_patrol_has_a_blind_centre_but_posts_do_not() -> None:
    board = Board(5, 5, 1, True)
    centre = Position(3, 3)
    # The four corners never see the centre cell (distance 2 from every corner)...
    assert not _covers(patrol.corners(board), centre, 1)
    # ...but the observation-post sweep does — this is the concrete improvement.
    assert _covers(patrol.patrol_route(board, radius=1), centre, 1)


def test_large_board_falls_back_to_corners() -> None:
    board = Board(9, 9, 1, True)  # radius-1 tiling would need 3x3=9 posts -> too many
    route = patrol.patrol_route(board, radius=1)
    assert {p.as_tuple() for p in route} == {(1, 1), (1, 9), (9, 1), (9, 9)}


def test_six_by_six_still_uses_posts() -> None:
    board = Board(6, 6, 1, True)  # ceil(6/3) = 2 posts/axis -> still small enough
    route = patrol.patrol_route(board, radius=1)
    assert {p.as_tuple() for p in route} == {(2, 2), (2, 5), (5, 2), (5, 5)}
    assert all(_covers(route, cell, 1) for cell in _all_cells(board))


def test_wider_vision_tiles_a_bigger_board() -> None:
    # With radius 2 each window is 5 wide, so an 8-wide board needs only 2 posts/axis.
    board = Board(8, 8, 1, True)
    route = patrol.patrol_route(board, radius=2)
    assert all(_covers(route, cell, 2) for cell in _all_cells(board))


def test_axis_posts_clamp_to_the_board() -> None:
    # Posts never sit so close to the edge that their window leaves the board.
    assert patrol._axis_posts(1, 5, 1) == [2, 4]
    assert patrol._axis_posts(1, 2, 1) == [1]  # tiny board: a single central post
