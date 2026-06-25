"""Blind-search patrol geometry for the cop.

When the cop loses sight of the thief it sweeps waypoints to re-acquire it. With Chebyshev
vision radius ``r`` each stop sees a ``(2r+1)x(2r+1)`` window. On a small board we visit
coverage-optimal *observation posts* whose windows tile the whole grid, so the cop has no
permanent blind spot — corners, by contrast, never see the centre cross (e.g. on 5x5 a
corner-only patrol can never spot a thief sitting at the middle cell).

On a larger board that tiling needs more posts than the cop can realistically sweep within
the move budget, so we fall back to the cheap four-corner circuit. The cutoff
(``_MAX_POSTS_PER_AXIS``) is where the tiling stops being a small, traversable set.
"""

from __future__ import annotations

from copthief.domain.board import Board
from copthief.domain.models import Position

_MAX_POSTS_PER_AXIS = 2  # use the tiling only while the sweep stays small/traversable


def _axis_posts(origin: int, length: int, radius: int) -> list[int]:
    """Window-centre coordinates whose radius-r spans tile ``[origin, origin+length-1]``."""
    window = 2 * radius + 1
    count = max(1, -(-length // window))  # ceil(length / window)
    far = origin + length - 1 - radius    # clamp so the last window stays on the board
    return sorted({min(origin + radius + i * window, far) for i in range(count)})


def observation_posts(board: Board, radius: int) -> tuple[list[int], list[int]]:
    """Per-axis observation-post coordinates that tile the board for vision ``radius``."""
    return (_axis_posts(board.origin, board.width, radius),
            _axis_posts(board.origin, board.height, radius))


def corners(board: Board) -> list[Position]:
    """The four board corners — the cheap fallback circuit on large boards."""
    xs = (board.origin, board.origin + board.width - 1)
    ys = (board.origin, board.origin + board.height - 1)
    return [Position(x, y) for x in xs for y in ys]


def patrol_route(board: Board, radius: int) -> list[Position]:
    """Blind-cop waypoints: tiling observation posts on small boards, else the corners."""
    xs, ys = observation_posts(board, radius)
    if len(xs) <= _MAX_POSTS_PER_AXIS and len(ys) <= _MAX_POSTS_PER_AXIS:
        return [Position(x, y) for x in xs for y in ys]
    return corners(board)
