"""Loading trained linear-policy weights into live play via the SDK."""

from __future__ import annotations

import numpy as np

from copthief.constants import Role
from copthief.sdk import CopThiefSDK
from copthief.shared.config import Config
from copthief.strategy.heuristic import HeuristicStrategy
from copthief.strategy.linear_q import LinearQStrategy


def test_sdk_loads_trained_linear_weights(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COPTHIEF_LLM_PROVIDER", "mock")
    sdk = CopThiefSDK(seed=0)
    np.save(tmp_path / "cop.npy", np.arange(8, dtype=float))
    sdk.config = Config({"strategy": {"linearq": {"cop_weights": "cop.npy"}}}, tmp_path)

    strat = LinearQStrategy(0.1, 0.9, 0.5)
    sdk._load_trained_weights(strat, Role.COP)
    assert np.allclose(strat.weights, np.arange(8))
    assert strat.epsilon == 0.0  # exploit the trained policy in play


def test_load_is_a_noop_for_non_linear_strategies() -> None:
    sdk = CopThiefSDK(seed=0)
    heuristic = HeuristicStrategy()
    sdk._load_trained_weights(heuristic, Role.COP)  # must not raise / has no weights


def test_load_is_a_noop_when_the_weights_file_is_missing(tmp_path) -> None:
    sdk = CopThiefSDK(seed=0)
    sdk.config = Config({"strategy": {"linearq": {"cop_weights": "absent.npy"}}}, tmp_path)
    strat = LinearQStrategy(0.1, 0.9, 0.5)
    before = strat.weights.copy()
    sdk._load_trained_weights(strat, Role.COP)
    assert np.allclose(strat.weights, before) and strat.epsilon == 0.5  # untouched
