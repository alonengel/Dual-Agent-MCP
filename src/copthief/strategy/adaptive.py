"""Adaptive strategy: anticipate the opponent's next cell from its last move.

This adapts mid-game to the enemy's behaviour rather than reacting only to its current
cell: the cop **intercepts** where the thief is heading; the thief **flees** from where
the cop is heading. It reuses the heuristic's cornering / mobility tie-breaks and its
need-based barrier rule, but aims them at the *predicted* opponent position.
"""

from __future__ import annotations

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position
from copthief.strategy.base import Strategy
from copthief.strategy.heuristic import HeuristicStrategy


def _sign(value: int) -> int:
    """Return -1, 0 or 1 — the direction of a one-dimensional displacement."""
    return (value > 0) - (value < 0)


class AdaptiveStrategy(Strategy):
    """Predicts the opponent's next position and targets that, adapting every turn."""

    def __init__(self, use_barriers: bool = False):
        self._heuristic = HeuristicStrategy(use_barriers)
        self._last_opponent: Position | None = None

    def decide(self, obs: Observation, opponent: Position, board: Board) -> Move:
        """Aim at the opponent's anticipated cell; still capture the real thief if next to it."""
        if obs.move_number == 0:
            self._last_opponent = None  # reset belief at the start of each subgame
        target = self._anticipate(opponent, board)
        self._last_opponent = opponent

        here = obs.self_pos
        if obs.role is Role.COP and opponent in board.free_neighbours(here):
            return Move(Role.COP, Action.MOVE, opponent.x - here.x, opponent.y - here.y)
        return self._heuristic.decide(obs, target, board)

    def _anticipate(self, opponent: Position, board: Board) -> Position:
        """Project one cell along the opponent's last observed movement direction."""
        if self._last_opponent is None:
            return opponent
        nxt = Position(opponent.x + _sign(opponent.x - self._last_opponent.x),
                       opponent.y + _sign(opponent.y - self._last_opponent.y))
        return nxt if board.in_bounds(nxt) else opponent

    def learn(self, reward: float) -> None:
        """Delegate the optional learning hook to the underlying heuristic (no-op)."""
        self._heuristic.learn(reward)
