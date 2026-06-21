"""Integration tests for the full self-play match pipeline."""

from __future__ import annotations

import random

from copthief.constants import Role
from copthief.llm.mock import MockProvider
from copthief.orchestrator.agent import Agent
from copthief.orchestrator.match import MatchRunner
from copthief.shared.logger import AuditLog
from copthief.strategy.heuristic import HeuristicStrategy


def _runner(game_cfg, scoring_cfg, tmp_path) -> MatchRunner:
    cop = Agent(Role.COP, HeuristicStrategy(), MockProvider())
    thief = Agent(Role.THIEF, HeuristicStrategy(), MockProvider())
    audit = AuditLog(tmp_path, {"log_dir": "logs", "game_log_file": "audit.log"})
    return MatchRunner(game_cfg, scoring_cfg, cop, thief, audit, random.Random(1))


def test_match_runs_all_subgames(game_cfg, scoring_cfg, tmp_path) -> None:
    result = _runner(game_cfg, scoring_cfg, tmp_path).run_match()
    assert len(result["sub_games"]) == game_cfg["num_games"]
    assert "cop" in result["totals"]
    assert "thief" in result["totals"]


def test_match_writes_audit_trail(game_cfg, scoring_cfg, tmp_path) -> None:
    runner = _runner(game_cfg, scoring_cfg, tmp_path)
    runner.run_match()
    lines = runner.audit.path.read_text(encoding="utf-8").splitlines()
    events = {__import__("json").loads(line)["event"] for line in lines}
    assert {"subgame_start", "turn", "subgame_end", "match_complete"} <= events


def test_capture_on_tiny_board_scores_cop(scoring_cfg, tmp_path) -> None:
    cfg = {"grid_size": [2, 2], "max_moves": 25, "num_games": 3,
           "max_barriers": 5, "origin": 1, "diagonal_moves": True}
    result = _runner(cfg, scoring_cfg, tmp_path).run_match()
    # On a 2x2 the cop reaches the thief quickly, so it should score points.
    assert result["totals"]["cop"] > 0
