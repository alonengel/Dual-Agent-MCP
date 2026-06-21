"""Tests for the scoring book and bonus calculation."""

from __future__ import annotations

from copthief.constants import Outcome
from copthief.domain.scoring import ScoreBook


def test_cop_win_scores(scoring_cfg: dict) -> None:
    book = ScoreBook(scoring_cfg)
    result = book.score_subgame(1, Outcome.COP_WIN, 4)
    assert result.cop_score == 20
    assert result.thief_score == 5


def test_thief_win_scores(scoring_cfg: dict) -> None:
    book = ScoreBook(scoring_cfg)
    result = book.score_subgame(2, Outcome.THIEF_WIN, 25)
    assert result.cop_score == 5
    assert result.thief_score == 10


def test_technical_loss_scores_zero(scoring_cfg: dict) -> None:
    book = ScoreBook(scoring_cfg)
    result = book.score_subgame(3, Outcome.TECHNICAL_LOSS, 0)
    assert result.cop_score == 0
    assert result.thief_score == 0


def test_max_total_is_ninety(scoring_cfg: dict) -> None:
    book = ScoreBook(scoring_cfg)
    cop_wins = [book.score_subgame(i, Outcome.COP_WIN, 4) for i in range(3)]
    thief_wins = [book.score_subgame(i, Outcome.THIEF_WIN, 25) for i in range(3)]
    totals = book.totals(cop_wins + thief_wins)
    assert totals["cop"] == 3 * 20 + 3 * 5
    assert totals["thief"] == 3 * 5 + 3 * 10


def test_bonus_points_mapping(scoring_cfg: dict) -> None:
    bonus = {"win": 10, "lose": 7, "tie": 5}
    assert ScoreBook.bonus_points(80, 60, bonus) == 10
    assert ScoreBook.bonus_points(60, 80, bonus) == 7
    assert ScoreBook.bonus_points(70, 70, bonus) == 5
