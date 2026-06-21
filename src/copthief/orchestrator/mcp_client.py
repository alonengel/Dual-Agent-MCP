"""Networked orchestrator: drives two remote agent MCP servers over HTTP.

This is the cloud / inter-group realisation of the same pipeline. The orchestrator
is the referee: it holds authoritative state, relays free-text messages between the
two servers, validates every action and writes the audit trail.
"""

from __future__ import annotations

import os
from typing import Any

from fastmcp import Client
from fastmcp.client.auth import BearerAuth

from copthief.constants import Action, Outcome, Role
from copthief.domain.models import Move
from copthief.domain.scoring import ScoreBook
from copthief.orchestrator.setup import build_subgame, observe
from copthief.shared.config import Config
from copthief.shared.logger import AuditLog


class NetworkMatch:
    """Runs a full match by calling the cop and thief MCP servers remotely."""

    def __init__(self, config: Config, audit: AuditLog):
        self.config = config
        self.audit = audit
        self.mcp = config.section("mcp")
        self.token = os.environ.get("COPTHIEF_MCP_TOKEN", "")
        self.scorebook = ScoreBook(config.section("scoring"))

    async def _ask(self, url: str, role: Role, obs, message: str) -> dict[str, Any]:
        """Call a remote agent's play_turn tool (bearer-authed) and return its payload."""
        auth = BearerAuth(self.token) if self.token else None
        async with Client(url, auth=auth) as client:
            result = await client.call_tool("play_turn", {
                "self_x": obs.self_pos.x, "self_y": obs.self_pos.y,
                "move_number": obs.move_number, "max_moves": obs.max_moves,
                "barriers_left": obs.barriers_left, "opponent_message": message,
            })
        return result.data

    async def _run_subgame(self, index: int, rng) -> Any:
        """Play one networked subgame to its terminal outcome."""
        game = build_subgame(self.config.section("game"), rng)
        urls = {Role.COP: self.mcp.get("cop_url"), Role.THIEF: self.mcp.get("thief_url")}
        message = ""
        while not game.finished():
            role = game.turn
            obs = observe(game, role, message)
            payload = await self._ask(urls[role], role, obs, message)
            move = Move(role, Action(payload["action"]), payload["dx"], payload["dy"])
            result = game.apply(move)
            message = payload["message"]
            self.audit.record("turn_net", index=index, role=role.value,
                              action=move.action.value, legal=result.legal,
                              cop=game.cop.as_tuple(), thief=game.thief.as_tuple())
        outcome = game.outcome or Outcome.TECHNICAL_LOSS
        return self.scorebook.score_subgame(index, outcome, game.move_number)

    async def run(self, rng) -> dict[str, Any]:
        """Play all subgames against the remote servers and aggregate scores."""
        results = [await self._run_subgame(i, rng)
                   for i in range(1, int(self.config.get("game.num_games", 6)) + 1)]
        totals = self.scorebook.totals(results)
        self.audit.record("match_complete_net", totals=totals)
        return {"sub_games": [r.to_dict() for r in results], "totals": totals}
