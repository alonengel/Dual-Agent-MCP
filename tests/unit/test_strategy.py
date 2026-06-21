"""Tests for heuristic and Q-learning strategies and the factory."""

from __future__ import annotations

import random

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.strategy.base import chebyshev
from copthief.strategy.factory import build_strategy
from copthief.strategy.heuristic import HeuristicStrategy
from copthief.strategy.qlearning import QTableStrategy, shaped_reward


def _obs(role: Role, here: Position) -> Observation:
    return Observation(role, here, 0, 25, 5)


def test_chebyshev_distance() -> None:
    assert chebyshev(Position(1, 1), Position(4, 3)) == 3


def test_cop_moves_closer(board: Board) -> None:
    strat = HeuristicStrategy()
    move = strat.decide(_obs(Role.COP, Position(1, 1)), Position(5, 5), board)
    assert move.action is Action.MOVE
    assert (move.dx, move.dy) == (1, 1)


def test_thief_moves_away(board: Board) -> None:
    strat = HeuristicStrategy()
    move = strat.decide(_obs(Role.THIEF, Position(3, 3)), Position(2, 2), board)
    new = Position(3 + move.dx, 3 + move.dy)
    assert chebyshev(new, Position(2, 2)) >= 1


def test_cop_steps_onto_adjacent_thief(board: Board) -> None:
    strat = HeuristicStrategy()
    move = strat.decide(_obs(Role.COP, Position(2, 2)), Position(3, 3), board)
    assert (move.dx, move.dy) == (1, 1)


def test_no_free_neighbours_stays() -> None:
    board = Board(1, 1, origin=1, diagonal=True)
    strat = HeuristicStrategy()
    move = strat.decide(_obs(Role.COP, Position(1, 1)), Position(1, 1), board)
    assert move.action is Action.STAY


def test_cop_blocks_only_when_stuck(board: Board) -> None:
    # Block the only distance-reducing neighbour so the cop cannot get closer.
    board.add_barrier(Position(2, 2))
    strat = HeuristicStrategy(use_barriers=True)
    move = strat.decide(_obs(Role.COP, Position(1, 1)), Position(5, 5), board)
    assert move.action is Action.BLOCK


def test_cop_does_not_block_when_it_can_advance(board: Board) -> None:
    strat = HeuristicStrategy(use_barriers=True)
    move = strat.decide(_obs(Role.COP, Position(1, 1)), Position(5, 5), board)
    assert move.action is Action.MOVE  # a diagonal step gets closer → no block


def test_cop_skips_barrier_when_adjacent(board: Board) -> None:
    strat = HeuristicStrategy(use_barriers=True)
    move = strat.decide(_obs(Role.COP, Position(2, 2)), Position(3, 3), board)
    assert move.action is Action.MOVE  # capture beats blocking


def test_factory_builds_heuristic_by_default() -> None:
    assert isinstance(build_strategy({}), HeuristicStrategy)


def test_factory_builds_qtable() -> None:
    strat = build_strategy({"kind": "qtable"}, random.Random(0))
    assert isinstance(strat, QTableStrategy)


def test_qtable_decides_and_learns(board: Board) -> None:
    strat = QTableStrategy(0.5, 0.9, 0.0, random.Random(0))
    move = strat.decide(_obs(Role.COP, Position(1, 1)), Position(3, 3), board)
    assert move.role is Role.COP
    strat.learn(reward=1.0)  # should update without error


def test_shaped_reward_signs() -> None:
    assert shaped_reward(Role.COP, before=4, after=2, captured=False) > 0
    assert shaped_reward(Role.THIEF, before=2, after=4, captured=False) > 0
    assert shaped_reward(Role.COP, before=1, after=0, captured=True) == 10.0
