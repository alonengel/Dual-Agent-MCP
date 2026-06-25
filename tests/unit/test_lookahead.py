"""Tests for the depth-1 minimax LookaheadStrategy."""

from __future__ import annotations

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.strategy.base import chebyshev
from copthief.strategy.factory import build_strategy
from copthief.strategy.heuristic import HeuristicStrategy
from copthief.strategy.lookahead import LookaheadStrategy, best_reply


def _obs(role: Role, here: Position) -> Observation:
    return Observation(role, here, 0, 25, 5)


def test_factory_builds_lookahead() -> None:
    assert isinstance(build_strategy({"kind": "lookahead"}), LookaheadStrategy)


def test_best_reply_flees_and_chases(board: Board) -> None:
    # Fleeing: pick the neighbour farthest from the target.
    flee = best_reply(Position(3, 3), Position(1, 1), board, fleeing=True)
    assert chebyshev(flee, Position(1, 1)) == 3
    # Chasing onto an adjacent target captures it outright.
    assert best_reply(Position(2, 2), Position(3, 3), board, fleeing=False) == Position(3, 3)
    # Chasing a distant target steps closer.
    chase = best_reply(Position(1, 1), Position(5, 5), board, fleeing=False)
    assert chebyshev(chase, Position(5, 5)) == 3


def test_cop_captures_adjacent_thief(board: Board) -> None:
    move = LookaheadStrategy().decide(_obs(Role.COP, Position(2, 2)), Position(3, 3), board)
    assert move.action is Action.MOVE and (move.dx, move.dy) == (1, 1)


def test_cop_closes_in(board: Board) -> None:
    move = LookaheadStrategy().decide(_obs(Role.COP, Position(1, 1)), Position(5, 5), board)
    new = Position(1 + move.dx, 1 + move.dy)
    assert chebyshev(new, Position(5, 5)) < chebyshev(Position(1, 1), Position(5, 5))


def test_thief_increases_distance(board: Board) -> None:
    move = LookaheadStrategy().decide(_obs(Role.THIEF, Position(3, 3)), Position(2, 2), board)
    new = Position(3 + move.dx, 3 + move.dy)
    assert chebyshev(new, Position(2, 2)) >= chebyshev(Position(3, 3), Position(2, 2))


def test_thief_never_worse_than_greedy_on_lookahead_objective(board: Board) -> None:
    """The lookahead thief keeps at least as much distance-after-chase as the greedy one.

    This is the property the strategy optimises: scoring by the post-reply distance can
    only match or beat the greedy heuristic on that very metric.
    """
    here, cop = Position(3, 3), Position(1, 1)

    def post_chase(move) -> int:
        cell = Position(here.x + move.dx, here.y + move.dy)
        return chebyshev(cell, best_reply(cop, cell, board, fleeing=False))

    look = LookaheadStrategy().decide(_obs(Role.THIEF, here), cop, board)
    greedy = HeuristicStrategy().decide(_obs(Role.THIEF, here), cop, board)
    assert post_chase(look) >= post_chase(greedy)


def test_cop_blocks_only_when_stuck(board: Board) -> None:
    board.add_barrier(Position(2, 2))  # seal the only distance-reducing step
    move = LookaheadStrategy(use_barriers=True).decide(
        _obs(Role.COP, Position(1, 1)), Position(5, 5), board)
    assert move.action is Action.BLOCK


def test_no_free_neighbours_stays() -> None:
    board = Board(1, 1, origin=1, diagonal=True)
    move = LookaheadStrategy().decide(_obs(Role.THIEF, Position(1, 1)), Position(1, 1), board)
    assert move.action is Action.STAY


def test_thief_hides_behind_barrier_wall() -> None:
    """With a wall capping the cop's approach, the thief prefers the protected pocket.

    The cop is boxed against column 1 by a barrier wall, so fleeing west keeps it far;
    this is exactly the edge/barrier exploitation greedy current-distance play misses.
    """
    board = Board(5, 5, origin=1, diagonal=True)
    for y in range(1, 6):
        board.add_barrier(Position(2, y))  # full wall at x=2, cop trapped in column 1
    cop, here = Position(1, 3), Position(3, 3)
    move = LookaheadStrategy().decide(_obs(Role.THIEF, here), cop, board)
    cell = Position(here.x + move.dx, here.y + move.dy)
    # The cop cannot cross the wall, so the thief's post-chase distance stays maximal.
    assert chebyshev(cell, best_reply(cop, cell, board, fleeing=False)) >= 2
