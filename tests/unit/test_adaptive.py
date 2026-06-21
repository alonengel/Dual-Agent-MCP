"""Tests for the anticipation-based AdaptiveStrategy."""

from __future__ import annotations

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.strategy.adaptive import AdaptiveStrategy
from copthief.strategy.base import chebyshev
from copthief.strategy.factory import build_strategy


def _obs(role: Role, here: Position, move: int = 0) -> Observation:
    return Observation(role, here, move, 25, 5)


def test_factory_builds_adaptive() -> None:
    assert isinstance(build_strategy({"kind": "adaptive"}), AdaptiveStrategy)


def test_cop_intercepts_projected_cell(board: Board) -> None:
    strat = AdaptiveStrategy()
    strat.decide(_obs(Role.COP, Position(1, 1), 0), Position(3, 3), board)  # seed history
    move = strat.decide(_obs(Role.COP, Position(2, 2), 1), Position(4, 4), board)
    assert (move.dx, move.dy) == (1, 1)  # aims at predicted (5,5), not current (4,4)


def test_cop_captures_actual_when_adjacent(board: Board) -> None:
    strat = AdaptiveStrategy()
    strat.decide(_obs(Role.COP, Position(1, 1), 0), Position(3, 3), board)
    move = strat.decide(_obs(Role.COP, Position(2, 2), 1), Position(3, 3), board)
    assert move.action is Action.MOVE
    assert (move.dx, move.dy) == (1, 1)  # steps onto the real thief at (3,3)


def test_thief_flees_from_projected_cell(board: Board) -> None:
    strat = AdaptiveStrategy()
    strat.decide(_obs(Role.THIEF, Position(3, 3), 0), Position(1, 1), board)
    move = strat.decide(_obs(Role.THIEF, Position(3, 3), 1), Position(2, 2), board)
    new = Position(3 + move.dx, 3 + move.dy)
    assert chebyshev(new, Position(3, 3)) >= 1  # moves away from predicted cop cell (3,3)


def test_reset_history_at_subgame_start(board: Board) -> None:
    strat = AdaptiveStrategy()
    strat.decide(_obs(Role.COP, Position(1, 1), 5), Position(5, 5), board)
    # move_number 0 must clear the stale belief so no spurious prediction is used
    move = strat.decide(_obs(Role.COP, Position(1, 1), 0), Position(5, 5), board)
    assert move.action is Action.MOVE
