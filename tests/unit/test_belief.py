"""Tests for the BeliefGrid Bayes filter and the BeliefStrategy.

Following the partner team's approach, the grid tests assert *invariants* (stays a
normalised distribution, barriers hold zero mass) rather than exact float values.
"""

from __future__ import annotations

import math

from copthief.belief.grid import BeliefGrid
from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.strategy.base import chebyshev
from copthief.strategy.belief import BeliefStrategy
from copthief.strategy.factory import build_strategy


def _board() -> Board:
    return Board(5, 5, origin=1, diagonal=True)


def _obs(role: Role, here: Position, move: int = 0) -> Observation:
    return Observation(role, here, move, 25, 5)


def _is_distribution(grid: BeliefGrid) -> bool:
    return math.isclose(float(grid.as_array().sum()), 1.0)


def test_uniform_prior_is_a_distribution_with_barriers_at_zero() -> None:
    board = _board()
    board.add_barrier(Position(3, 3))
    grid = BeliefGrid(board)
    assert _is_distribution(grid)
    assert grid.as_array()[3 - 1, 3 - 1] == 0.0  # barrier carries no mass


def test_set_point_and_most_likely() -> None:
    grid = BeliefGrid(_board())
    grid.set_point(Position(4, 2))
    assert _is_distribution(grid)
    assert grid.most_likely() == Position(4, 2)


def test_diffuse_spreads_a_point_to_neighbours_and_stays_normalised() -> None:
    grid = BeliefGrid(_board())
    grid.set_point(Position(3, 3))
    grid.diffuse()
    assert _is_distribution(grid)
    arr = grid.as_array()
    assert arr[3 - 1, 3 - 1] == 0.0          # the point handed all its mass away
    assert arr[2 - 1, 2 - 1] > 0.0           # a neighbour received some


def test_observe_not_at_zeroes_a_cell() -> None:
    grid = BeliefGrid(_board())
    grid.observe_not_at(Position(1, 1))
    assert _is_distribution(grid)
    assert grid.as_array()[0, 0] == 0.0


def test_observe_not_at_falling_to_uniform_when_mass_exhausted() -> None:
    board = Board(1, 1, origin=1, diagonal=True)  # single free cell holds all mass
    grid = BeliefGrid(board)
    grid.observe_not_at(Position(1, 1))
    assert _is_distribution(grid)  # reset to uniform rather than going all-zero


def test_observe_claim_shifts_mass_toward_the_claim() -> None:
    grid = BeliefGrid(_board())
    before = grid.as_array()[5 - 1, 5 - 1]
    grid.observe_claim(Position(5, 5), discount=0.5)
    assert _is_distribution(grid)
    assert grid.as_array()[5 - 1, 5 - 1] > before
    assert grid.most_likely() == Position(5, 5)


def test_observe_claim_zero_discount_is_a_noop() -> None:
    grid = BeliefGrid(_board())
    arr = grid.as_array()
    grid.observe_claim(Position(5, 5), discount=0.0)
    assert (grid.as_array() == arr).all()


def test_expected_distance_zero_for_a_point_belief() -> None:
    grid = BeliefGrid(_board())
    grid.set_point(Position(2, 2))
    assert grid.expected_distance(Position(2, 2)) == 0.0
    assert grid.expected_distance(Position(5, 5)) == chebyshev(Position(2, 2), Position(5, 5))


def test_factory_builds_belief() -> None:
    assert isinstance(build_strategy({"kind": "belief"}), BeliefStrategy)


def test_belief_collapses_on_a_sighting_and_captures_adjacent() -> None:
    # A rival within sight_radius (1) is a confirmed sighting: belief collapses to that cell
    # and the lookahead captures it. Also exercises the no-op learn hook.
    strat = BeliefStrategy()
    move = strat.decide(_obs(Role.COP, Position(3, 3)), Position(4, 4), _board())
    assert move.action is Action.MOVE and (move.dx, move.dy) == (1, 1)
    strat.learn(0.0)


def test_belief_cop_moves_toward_a_strong_claim() -> None:
    # A single high-discount claim makes (5,5) the most-likely cell -> cop steps that way.
    strat = BeliefStrategy(claim_discount=0.9)
    move = strat.decide(_obs(Role.COP, Position(1, 1)), Position(5, 5), _board())
    assert move.action is Action.MOVE and (move.dx, move.dy) == (1, 1)


def test_belief_thief_keeps_distance_and_runs_two_plies() -> None:
    board = _board()
    strat = BeliefStrategy(claim_discount=0.9)
    strat.decide(_obs(Role.THIEF, Position(3, 3), 0), Position(2, 2), board)  # seeds the grid
    move = strat.decide(_obs(Role.THIEF, Position(3, 3), 1), Position(2, 2), board)  # diffuse path
    new = Position(3 + move.dx, 3 + move.dy)
    assert chebyshev(new, Position(2, 2)) >= chebyshev(Position(3, 3), Position(2, 2))
