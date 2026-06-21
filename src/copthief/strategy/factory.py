"""Factory that builds a strategy instance from configuration."""

from __future__ import annotations

import random
from typing import Any

from copthief.strategy.adaptive import AdaptiveStrategy
from copthief.strategy.base import Strategy
from copthief.strategy.heuristic import HeuristicStrategy
from copthief.strategy.qlearning import QTableStrategy


def build_strategy(cfg: dict[str, Any], rng: random.Random | None = None) -> Strategy:
    """Return the configured strategy ('heuristic', 'adaptive' or 'qtable')."""
    kind = str(cfg.get("kind", "heuristic")).lower()
    barriers = bool(cfg.get("cop_uses_barriers", False))
    if kind == "qtable":
        params = cfg.get("qtable", {})
        return QTableStrategy(
            learning_rate=float(params.get("learning_rate", 0.1)),
            discount_factor=float(params.get("discount_factor", 0.9)),
            epsilon=float(params.get("epsilon", 0.1)),
            rng=rng,
        )
    if kind == "adaptive":
        return AdaptiveStrategy(use_barriers=barriers)
    return HeuristicStrategy(use_barriers=barriers)
