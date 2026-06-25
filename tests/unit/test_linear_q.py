"""Tests for the linear-function-approximation LinearQStrategy (afterstate MC value)."""

from __future__ import annotations

import random

import numpy as np

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.strategy.factory import build_strategy
from copthief.strategy.linear_q import _FEATURES, LinearQStrategy


def _board() -> Board:
    return Board(5, 5, origin=1, diagonal=True)


def _obs(role: Role, here: Position) -> Observation:
    return Observation(role, here, 0, 25, 5)


def test_factory_builds_linearq() -> None:
    assert isinstance(build_strategy({"kind": "linearq"}), LinearQStrategy)


def test_decide_returns_a_legal_move() -> None:
    strat = LinearQStrategy(0.05, 0.9, 0.0, random.Random(0))
    move = strat.decide(_obs(Role.COP, Position(1, 1)), Position(5, 5), _board())
    assert move.action in (Action.MOVE, Action.STAY)
    if move.action is Action.MOVE:
        assert _board().is_free(Position(1 + move.dx, 1 + move.dy))


def test_features_are_normalised_and_sized() -> None:
    strat = LinearQStrategy(0.05, 0.9, 0.0)
    phi = strat._features(Position(2, 2), Position(4, 4), _board(), Role.COP)
    assert phi.shape == (len(_FEATURES),)
    assert phi[0] == 1.0                       # bias term
    assert (phi >= 0.0).all() and (phi <= 1.0).all()


def test_learn_buffers_then_end_episode_updates_weights() -> None:
    strat = LinearQStrategy(0.5, 0.9, 0.0, random.Random(0))
    strat.decide(_obs(Role.COP, Position(1, 1)), Position(2, 2), _board())
    strat.learn(1.0)
    assert strat._episode  # buffered, not yet applied
    before = strat.weights.copy()
    strat.end_episode()
    assert not strat._episode                  # buffer cleared
    assert not np.allclose(strat.weights, before)  # Monte-Carlo update moved the weights


def test_learn_without_a_prior_decide_is_a_noop() -> None:
    strat = LinearQStrategy(0.5, 0.9, 0.0)
    strat.learn(1.0)       # no _last_phi recorded yet
    strat.end_episode()
    assert np.allclose(strat.weights, 0.0)
