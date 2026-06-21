"""Strategy interface and shared distance helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position


def chebyshev(a: Position, b: Position) -> int:
    """8-directional (king-move) distance between two cells."""
    return max(abs(a.x - b.x), abs(a.y - b.y))


class Strategy(ABC):
    """Chooses a concrete :class:`Move` from a partial observation."""

    @abstractmethod
    def decide(self, obs: Observation, opponent: Position, board: Board) -> Move:
        """Return the next move for the observing agent.

        ``opponent`` is the agent's *belief* about the rival's cell, derived from
        the natural-language dialogue (it may be exact in self-play).
        """

    def learn(self, reward: float) -> None:  # noqa: B027 - optional hook
        """Optional post-move learning hook; no-op for stateless strategies."""
