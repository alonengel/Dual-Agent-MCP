"""Scoring rules. Values are injected from config; the cop-win = 20 invariant is fixed."""

from __future__ import annotations

from copthief.constants import Outcome, Role
from copthief.domain.models import SubgameResult


class ScoreBook:
    """Computes per-subgame scores and aggregates totals for a full match."""

    def __init__(self, scoring: dict[str, int]):
        self.cop_win = int(scoring.get("cop_win", 20))
        self.thief_win = int(scoring.get("thief_win", 10))
        self.cop_loss = int(scoring.get("cop_loss", 5))
        self.thief_loss = int(scoring.get("thief_loss", 5))

    def score_subgame(self, index: int, outcome: Outcome, moves_played: int) -> SubgameResult:
        """Return the scored result of one subgame from its outcome."""
        if outcome is Outcome.COP_WIN:
            cop, thief = self.cop_win, self.thief_loss
        elif outcome is Outcome.THIEF_WIN:
            cop, thief = self.cop_loss, self.thief_win
        else:  # technical loss: no points awarded; subgame must be replayed
            cop, thief = 0, 0
        return SubgameResult(index, outcome, moves_played, cop, thief)

    @staticmethod
    def totals(results: list[SubgameResult]) -> dict[str, int]:
        """Sum cop and thief points across all valid subgames."""
        return {
            Role.COP.value: sum(r.cop_score for r in results),
            Role.THIEF.value: sum(r.thief_score for r in results),
        }

    @staticmethod
    def bonus_points(my_total: int, opponent_total: int, bonus: dict[str, int]) -> int:
        """Map a head-to-head total comparison to inter-group bonus points."""
        if my_total > opponent_total:
            return int(bonus.get("win", 10))
        if my_total < opponent_total:
            return int(bonus.get("lose", 7))
        return int(bonus.get("tie", 5))
