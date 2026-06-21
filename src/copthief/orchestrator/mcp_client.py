"""Networked orchestrator (the MCP *client*), faithful to PDF section 5.2.

The client owns the LLM and the game logic: it builds each agent's observation,
decides the move (strategy), verbalises it (LLM), and then calls the agent's
**pure** MCP tools (`reset`/`move`/`place_barrier`/`note`) over HTTP to execute.
The client is the authoritative referee; the servers hold no LLM.
"""

from __future__ import annotations

import os
from typing import Any

from fastmcp import Client
from fastmcp.client.auth import BearerAuth

from copthief.constants import Action, Outcome, Role
from copthief.domain.scoring import ScoreBook
from copthief.llm.factory import build_provider
from copthief.orchestrator import negotiation, perception
from copthief.orchestrator.agent import Agent
from copthief.orchestrator.match import opponent_position
from copthief.orchestrator.setup import build_subgame, observe
from copthief.shared.config import Config
from copthief.shared.logger import AuditLog
from copthief.strategy.factory import build_strategy


class NetworkMatch:
    """Runs a full match by driving two remote, LLM-free agent servers."""

    def __init__(self, config: Config, audit: AuditLog):
        self.config = config
        self.audit = audit
        self.mcp = config.section("mcp")
        self.token = os.environ.get("COPTHIEF_MCP_TOKEN", "")
        self.scorebook = ScoreBook(config.section("scoring"))
        self.urls = {Role.COP: self.mcp.get("cop_url"), Role.THIEF: self.mcp.get("thief_url")}
        self.agents = {r: Agent(r, build_strategy(config.section("strategy")),
                                build_provider(config.section("llm"))) for r in Role}
        game = config.section("game")
        self.radius, self.radius_mode = negotiation.negotiated_radius(game)
        self.exact = str(game.get("disclosure", "exact")).lower() == "exact"
        self.deception = bool(game.get("deception", False))

    async def _call(self, role: Role, tool: str, args: dict[str, Any]) -> Any:
        """Invoke a tool on the given agent's MCP server (bearer-authed)."""
        auth = BearerAuth(self.token) if self.token else None
        async with Client(self.urls[role], auth=auth) as client:
            result = await client.call_tool(tool, args)
        return result.data

    async def _execute(self, role: Role, move) -> None:
        """Mirror a validated move onto the agent's remote server state."""
        if move.action is Action.BLOCK:
            await self._call(role, "place_barrier", {})
        elif move.action is Action.MOVE:
            await self._call(role, "move", {"dx": move.dx, "dy": move.dy})

    async def _turn(self, game, index: int, message: str) -> str:
        """One turn under partial observation: perceive, decide, execute via tools, relay."""
        role = game.turn
        agent = self.agents[role]
        opponent = self.agents[Role.THIEF if role is Role.COP else Role.COP]
        opp_true = opponent_position(game, role)

        agent.perceive(game.position_of(role), opp_true, self.radius)
        obs = observe(game, role, message)
        target = agent.belief or perception.center(game.board)
        move = agent.decide(obs, game.board, fallback_opponent=target)
        result = game.apply(move)               # client is the authoritative referee
        await self._execute(role, move)         # server executes the same action

        disclosed = perception.disclosed_cell(result.new_pos, opp_true, self.radius,
                                              self.exact, self.deception, game.board, self.rng)
        msg = agent.voice(obs, move, disclosed)
        perception.relay(opponent, result.new_pos, opp_true, self.radius, msg)
        await self._call(Role.THIEF if role is Role.COP else Role.COP, "note",
                         {"message": msg})
        self.audit.record("turn_net", index=index, role=role.value,
                          action=move.action.value, legal=result.legal,
                          cop=game.cop.as_tuple(), thief=game.thief.as_tuple(), message=msg)
        return msg

    async def _run_subgame(self, index: int, rng) -> Any:
        """Reset both servers, then play one subgame to its terminal outcome."""
        game = build_subgame(self.config.section("game"), rng)
        await self._call(Role.COP, "reset", {"x": game.cop.x, "y": game.cop.y,
                                             "barriers_left": game.barriers_left})
        await self._call(Role.THIEF, "reset", {"x": game.thief.x, "y": game.thief.y,
                                               "barriers_left": game.barriers_left})
        message = ""
        while not game.finished():
            message = await self._turn(game, index, message)
        outcome = game.outcome or Outcome.TECHNICAL_LOSS
        return self.scorebook.score_subgame(index, outcome, game.move_number)

    async def _negotiate(self) -> None:
        """Opening free-language handshake; relayed to each server via the note tool."""
        messages = negotiation.opening_messages(self.agents[Role.COP],
                                                self.agents[Role.THIEF],
                                                self.config.section("game"))
        for role, message in messages.items():
            self.audit.record("negotiation", role=role.value, message=message)
        self.audit.record("vision_negotiation", radius=self.radius, outcome=self.radius_mode)
        await self._call(Role.THIEF, "note", {"message": messages[Role.COP]})
        await self._call(Role.COP, "note", {"message": messages[Role.THIEF]})

    async def _valid_subgame(self, index: int, rng, max_attempts: int = 3) -> Any:
        """Play a subgame, re-running technical failures (PDF 9: void & replay)."""
        for attempt in range(1, max_attempts + 1):
            try:
                return await self._run_subgame(index, rng)
            except Exception as exc:  # noqa: BLE001 - a failed subgame is void; retry it
                self.audit.record("technical_loss", index=index, attempt=attempt,
                                  error=str(exc))
        raise RuntimeError(f"subgame {index} failed after {max_attempts} attempts")

    async def run(self, rng) -> dict[str, Any]:
        """Play all subgames against the remote servers and aggregate scores."""
        self.rng = rng
        await self._negotiate()
        results = [await self._valid_subgame(i, rng)
                   for i in range(1, int(self.config.get("game.num_games", 6)) + 1)]
        totals = self.scorebook.totals(results)
        self.audit.record("match_complete_net", totals=totals)
        return {"sub_games": [r.to_dict() for r in results], "totals": totals}
