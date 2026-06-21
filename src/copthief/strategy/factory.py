"""Factory that builds a strategy instance from configuration."""

from __future__ import annotations

import random
from typing import Any

from copthief.strategy.base import Strategy
from copthief.strategy.heuristic import HeuristicStrategy
from copthief.strategy.qlearning import QTableStrategy


def build_strategy(cfg: dict[str, Any], rng: random.Random | None = None) -> Strategy:
    """Return the configured strategy ('heuristic' or 'qtable')."""
    kind = str(cfg.get("kind", "heuristic")).lower()
    if kind == "qtable":
        params = cfg.get("qtable", {})
        return QTableStrategy(
            learning_rate=float(params.get("learning_rate", 0.1)),
            discount_factor=float(params.get("discount_factor", 0.9)),
            epsilon=float(params.get("epsilon", 0.1)),
            rng=rng,
        )
    return HeuristicStrategy()
