"""Serve both agents under ONE HTTP endpoint, path-routed.

This lets a single public URL (e.g. an ngrok free-tier tunnel, or one free PaaS
service) expose both MCP servers at `/cop/mcp` and `/thief/mcp`. The two FastMCP
apps are mounted under a parent Starlette app whose lifespan drives both session
managers. Bearer-token auth still applies per sub-app.
"""

from __future__ import annotations

import contextlib

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount

from copthief.agents.server import build_server
from copthief.constants import Role
from copthief.shared.config import Config


def build_combined_app(config: Config | None = None):
    """Return (Starlette app mounting both agents, mcp config section)."""
    config = config or Config.load()
    cop, mcp_cfg = build_server(Role.COP, config)
    thief, _ = build_server(Role.THIEF, config)
    cop_app = cop.http_app(path="/mcp")
    thief_app = thief.http_app(path="/mcp")

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with cop_app.lifespan(app), thief_app.lifespan(app):
            yield

    app = Starlette(
        routes=[Mount("/cop", app=cop_app), Mount("/thief", app=thief_app)],
        lifespan=lifespan,
    )
    return app, mcp_cfg


def run_combined() -> None:
    """Start one HTTP server exposing /cop/mcp and /thief/mcp."""
    app, mcp_cfg = build_combined_app()
    uvicorn.run(app, host=mcp_cfg.get("host", "127.0.0.1"),
                port=int(mcp_cfg.get("combined_port", 8080)))
