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
    def reset(x: int, y: int, barriers_left: int) -> dict:
        """Start a new subgame: place this agent and clear its memory."""
        return session.reset(x, y, barriers_left)

    @mcp.tool
    def observe() -> dict:
        """Return this agent's partial view of the board."""
        return session.observe()

    @mcp.tool
    def move(dx: int, dy: int) -> dict:
        """Execute a one-step move and return the resulting position + legality."""
        return session.move(dx, dy)

    @mcp.tool
    def place_barrier() -> dict:
        """Cop-only: drop a barrier on the current cell."""
        return session.place_barrier()

    @mcp.tool
    def note(message: str) -> dict:
        """Record an opponent's free-text message for this agent."""
        return session.note(message)

    return mcp, config.section("mcp")


def run_server(role: Role) -> None:
    """Start the agent's HTTP MCP server on its configured port."""
    mcp, mcp_cfg = build_server(role)
    port = mcp_cfg.get("cop_port" if role is Role.COP else "thief_port", 8181)
    mcp.run(transport="http", host=mcp_cfg.get("host", "127.0.0.1"), port=int(port))
