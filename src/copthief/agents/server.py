"""FastMCP server that exposes one agent (cop or thief) over HTTP.

HTTP transport is used even locally, as the lecture insists, to prepare for the
cloud step. A shared token guards every tool so access can be revoked at will.
"""

from __future__ import annotations

import os

from fastmcp import FastMCP

from copthief.agents.session import AgentSession
from copthief.constants import Role
from copthief.shared.config import Config


def _check_token(token: str) -> None:
    """Reject calls whose token does not match the configured secret."""
    expected = os.environ.get("COPTHIEF_MCP_TOKEN", "")
    if not expected or token != expected:
        raise PermissionError("invalid or missing MCP token")


def build_server(role: Role, config: Config | None = None) -> tuple[FastMCP, dict]:
    """Create a FastMCP server for ``role`` and return it with its mcp config."""
    config = config or Config.load()
    session = AgentSession(role, config)
    mcp = FastMCP(f"{role.value.capitalize()} Agent")

    @mcp.tool
    def agree_protocol(grid: list[int], origin: int, token: str) -> str:
        """Return this agent's free-text protocol-agreement message."""
        _check_token(token)
        return session.agree_protocol(grid, origin)

    @mcp.tool
    def play_turn(self_x: int, self_y: int, move_number: int, max_moves: int,
                  barriers_left: int, opponent_message: str, token: str) -> dict:
        """Decide and return this agent's next action plus a natural-language message."""
        _check_token(token)
        return session.play_turn(self_x, self_y, move_number, max_moves,
                                 barriers_left, opponent_message)

    return mcp, config.section("mcp")


def run_server(role: Role) -> None:
    """Start the agent's HTTP MCP server on its configured port."""
    mcp, mcp_cfg = build_server(role)
    port = mcp_cfg.get("cop_port" if role is Role.COP else "thief_port", 8181)
    mcp.run(transport="http", host=mcp_cfg.get("host", "127.0.0.1"), port=int(port))
