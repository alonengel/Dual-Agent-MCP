"""FastMCP server that exposes one agent (cop or thief) over HTTP.

HTTP transport is used even locally, as the lecture insists, to prepare for the
cloud step. Access is guarded by transport-level **bearer-token** auth: clients must
send `Authorization: Bearer <token>`; rotating/clearing the token revokes access.
"""

from __future__ import annotations

import logging
import os

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from copthief.agents.session import AgentSession
from copthief.constants import Role
from copthief.shared.config import Config

_log = logging.getLogger("copthief.agents.server")


def _auth() -> StaticTokenVerifier | None:
    """Build a static bearer-token verifier from COPTHIEF_MCP_TOKEN (None if unset)."""
    token = os.environ.get("COPTHIEF_MCP_TOKEN", "")
    if not token:
        _log.warning("COPTHIEF_MCP_TOKEN not set; MCP server running WITHOUT auth")
        return None
    return StaticTokenVerifier(tokens={token: {"client_id": "copthief", "scopes": []}})


def build_server(role: Role, config: Config | None = None) -> tuple[FastMCP, dict]:
    """Create a FastMCP server for ``role`` and return it with its mcp config."""
    config = config or Config.load()
    session = AgentSession(role, config)
    mcp = FastMCP(f"{role.value.capitalize()} Agent", auth=_auth())

    @mcp.tool
    def agree_protocol(grid: list[int], origin: int) -> str:
        """Return this agent's free-text protocol-agreement message."""
        return session.agree_protocol(grid, origin)

    @mcp.tool
    def play_turn(self_x: int, self_y: int, move_number: int, max_moves: int,
                  barriers_left: int, opponent_message: str) -> dict:
        """Decide and return this agent's next action plus a natural-language message."""
        return session.play_turn(self_x, self_y, move_number, max_moves,
                                 barriers_left, opponent_message)

    return mcp, config.section("mcp")


def run_server(role: Role) -> None:
    """Start the agent's HTTP MCP server on its configured port."""
    mcp, mcp_cfg = build_server(role)
    port = mcp_cfg.get("cop_port" if role is Role.COP else "thief_port", 8181)
    mcp.run(transport="http", host=mcp_cfg.get("host", "127.0.0.1"), port=int(port))
