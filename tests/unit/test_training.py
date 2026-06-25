"""Tests for the reinforcement-learning trainer (short, deterministic runs)."""

from __future__ import annotations

import math
import random

import numpy as np

from copthief.strategy.qlearning import QTableStrategy
from copthief.training import TrainConfig, _epsilon, evaluate, train


def test_epsilon_anneals_from_start_to_end() -> None:
    assert _epsilon(0, 10, 0.5, 0.02) == 0.5
    assert math.isclose(_epsilon(9, 10, 0.5, 0.02), 0.02)
    assert _epsilon(0, 1, 0.5, 0.02) == 0.02  # degenerate single-step run


def test_train_returns_tables_and_curve() -> None:
    cfg = TrainConfig(games=20, eval_every=10, eval_games=20, grid=5, rounds=4, seed=1)
    out = train(cfg)
    assert out["q_cop"].shape == out["q_thief"].shape  # both Q-tables built
    assert len(out["curve"]) == 2  # two checkpoints at 10 and 20 games
    for point in out["curve"]:
        assert set(point) == {"games", "epsilon", "cop_winrate_vs_heuristic"}
        assert 0.0 <= point["cop_winrate_vs_heuristic"] <= 1.0


def test_evaluate_returns_a_fraction() -> None:
    cfg = TrainConfig(grid=5, rounds=4)
    untrained = QTableStrategy(0.1, 0.9, 0.0).q  # all-zero table
    win_rate = evaluate(untrained, cfg, random.Random(0), games=10)
    assert 0.0 <= win_rate <= 1.0


def test_training_beats_the_untrained_baseline() -> None:
    # The whole point: a trained cop must out-perform the untrained (all-zero) policy.
    cfg = TrainConfig(games=300, eval_every=300, eval_games=150, grid=5, rounds=4, seed=3)
    out = train(cfg)
    baseline = evaluate(np.zeros_like(out["q_cop"]), cfg, random.Random(99), cfg.eval_games)
    trained = out["curve"][-1]["cop_winrate_vs_heuristic"]
    assert trained > baseline
