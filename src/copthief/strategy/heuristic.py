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
            best = self._best_for_cop(candidates, opponent, board)
        else:
            best = self._best_for_thief(candidates, opponent, board)
        dx, dy = best.x - here.x, best.y - here.y
        return Move(obs.role, Action.MOVE, dx, dy)

    @staticmethod
    def _best_for_thief(candidates: list[Position], opponent: Position, board: Board) -> Position:
        """Flee: maximise distance from the cop, tie-broken by staying mobile."""
        far = max(chebyshev(c, opponent) for c in candidates)
        best = [c for c in candidates if chebyshev(c, opponent) == far]
        return max(best, key=lambda c: len(board.free_neighbours(c)))

    @staticmethod
    def _best_for_cop(candidates: list[Position], opponent: Position, board: Board) -> Position:
        """Close in: minimise distance, tie-broken by cutting the thief's escapes.

        When several equidistant steps exist, prefer the one that occupies a cell the
        thief could flee to, shrinking its mobility and herding it toward the walls.
        """
        if opponent in candidates:
            return opponent
        near = min(chebyshev(c, opponent) for c in candidates)
        best = [c for c in candidates if chebyshev(c, opponent) == near]
        return min(best, key=lambda c: _thief_escapes(opponent, c, board))


def _thief_escapes(thief: Position, cop_cell: Position, board: Board) -> int:
    """Count the thief's free neighbours, excluding the cell the cop would occupy."""
    return sum(1 for n in board.free_neighbours(thief) if n != cop_cell)
