"""The CopThief SDK: assembles components from config and exposes top-level actions.

External consumers never touch internal modules directly; they call this facade.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from copthief.constants import Role
from copthief.llm.factory import build_llm_clients, build_provider
from copthief.orchestrator.agent import Agent
from copthief.orchestrator.match import MatchRunner
from copthief.reporting.report import build_internal_report, save_report
from copthief.shared.config import Config
from copthief.shared.logger import AuditLog, setup_logging
from copthief.strategy.factory import build_strategy

if TYPE_CHECKING:
    from copthief.domain.subgame import Subgame


class CopThiefSDK:
    """Single entry point for running games and producing reports."""

    def __init__(self, config: Config | None = None, seed: int | None = None):
        self.config = config or Config.load()
        log_cfg = _read_json(self.config.root / "config/logging_config.json")
        self.logger = setup_logging(self.config.root, log_cfg)
        self.audit = AuditLog(self.config.root, log_cfg)
        self.rng = random.Random(seed)
        # One shared gatekeeper + usage meter for every external LLM call.
        self.gate, self.meter = build_llm_clients(self.config)

    def _build_agent(self, role: Role) -> Agent:
        """Construct an agent with its own strategy instance and LLM voice."""
        strategy = build_strategy(self.config.section("strategy"), self.rng)
        provider = build_provider(self.config.section("llm"), self.gate, self.meter)
        return Agent(role, strategy, provider)

    def run_self_play(self, games: int | None = None,
                      reporter: Callable[[str], None] | None = None,
                      board_render: Callable[[Subgame], str] | None = None) -> dict[str, Any]:
        """Run a local self-game and return the match result dict.

        ``games`` overrides the configured subgame count (handy for short demos);
        ``reporter`` receives human-readable progress for live dialogue output;
        ``board_render`` turns each turn's state into a live board for the terminal.
        """
        cop = self._build_agent(Role.COP)
        thief = self._build_agent(Role.THIEF)
        game_cfg = self.config.section("game")
        if games is not None:
            game_cfg = {**game_cfg, "num_games": games}
        runner = MatchRunner(
            game_cfg=game_cfg,
            scoring=self.config.section("scoring"),
            cop=cop, thief=thief, audit=self.audit, rng=self.rng, reporter=reporter,
            board_render=board_render,
        )
        self.logger.info("starting self-play match")
        result = runner.run_match()
        self.logger.info("self-play totals: %s", result["totals"])
        return result

    def run_network_match(self) -> dict[str, Any]:
        """Drive the two remote MCP servers over HTTP and return the result."""
        import asyncio

        from copthief.orchestrator.mcp_client import NetworkMatch

        net = NetworkMatch(self.config, self.audit)
        self.logger.info("starting networked match against MCP servers")
        result = asyncio.run(net.run(self.rng))
        self.logger.info("networked totals: %s", result["totals"])
        return result

    def report_and_save(self, match: dict[str, Any]) -> Path:
        """Build the internal JSON report from a match result and persist it."""
        report = build_internal_report(
            self.config.section("team"), self.config.section("mcp"), match
        )
        results_dir = self.config.root / self.config.get("reporting.results_dir", "results")
        path = save_report(report, results_dir, prefix="internal")
        self.logger.info("report saved: %s", path)
        usage = self.meter.summary()
        if usage["totals"]["calls"]:
            save_report(usage, results_dir, prefix="usage")
            self.logger.info("llm usage: %s", usage["totals"])
        return path


def _read_json(path: Path) -> dict[str, Any]:
    """Load a JSON config file into a dict."""
    import json

    return json.loads(path.read_text(encoding="utf-8"))
