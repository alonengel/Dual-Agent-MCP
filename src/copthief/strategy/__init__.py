"""Decision-making strategies for choosing an agent's next move.

Strategy is explicitly *secondary* to the pipeline in this assignment, so the
default is a transparent heuristic; a tabular Q-learning option is also provided.
"""

from copthief.strategy.base import Strategy
from copthief.strategy.factory import build_strategy

__all__ = ["Strategy", "build_strategy"]
