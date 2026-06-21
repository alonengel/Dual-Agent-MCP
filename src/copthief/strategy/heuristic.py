"""Greedy distance heuristics: the cop closes in, the thief flees."""

from __future__ import annotations

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position
from copthief.strategy.base import Strategy, chebyshev


class HeuristicStrategy(Strategy):
    """Cop minimises distance to the thief; thief maximises distance from the cop."""

    def decide(self, obs: Observation, opponent: Position, board: Board) -> Move:
        """Pick the neighbour that best serves the agent's role objective."""
        here = obs.self_pos
        candidates = board.free_neighbours(here)
        if not candidates:
            return Move(obs.role, Action.STAY)

        if obs.role is Role.COP:
            best = self._best_for_cop(candidates, opponent)
        else:
            best = self._best_for_thief(candidates, opponent)
        dx, dy = best.x - here.x, best.y - here.y
        return Move(obs.role, Action.MOVE, dx, dy)

    @staticmethod
    def _best_for_thief(candidates: list[Position], opponent: Position) -> Position:
        """Choose the reachable cell furthest from the cop."""
        return max(candidates, key=lambda c: chebyshev(c, opponent))

    @staticmethod
    def _best_for_cop(candidates: list[Position], opponent: Position) -> Position:
        """Choose the reachable cell closest to the thief (step onto it if adjacent)."""
        if opponent in candidates:
            return opponent
        return min(candidates, key=lambda c: chebyshev(c, opponent))
