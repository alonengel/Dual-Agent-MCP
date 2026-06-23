"""Persistent MCP HTTP sessions for networked matches."""

from __future__ import annotations

import contextlib
from typing import Any

from fastmcp import Client
from fastmcp.client.auth import BearerAuth
from fastmcp.client.transports import StreamableHttpTransport

from copthief.constants import Role

# ngrok free tier serves a browser-warning interstitial unless this header is set.
_SKIP_NGROK = {"ngrok-skip-browser-warning": "true"}


class PersistentMcpSession:
    """One connection per agent; reconnect once when a tunnel drops an idle link."""

    def __init__(self, urls: dict[Role, str], token: str = ""):
        self._urls = urls
        self._token = token
        self._clients: dict[Role, Client] = {}

    def _transport(self, role: Role) -> StreamableHttpTransport:
        auth = BearerAuth(self._token) if self._token else None
        return StreamableHttpTransport(self._urls[role], auth=auth, headers=_SKIP_NGROK)

    async def open(self) -> None:
        for role in Role:
            client = Client(self._transport(role))
            await client.__aenter__()
            self._clients[role] = client

    async def close(self) -> None:
        for client in self._clients.values():
            with contextlib.suppress(Exception):
                await client.__aexit__(None, None, None)
        self._clients.clear()

    async def _reconnect(self, role: Role) -> None:
        with contextlib.suppress(Exception):
            await self._clients[role].__aexit__(None, None, None)
        client = Client(self._transport(role))
        await client.__aenter__()
        self._clients[role] = client

    async def call(self, role: Role, tool: str, args: dict[str, Any]) -> Any:
        try:
            result = await self._clients[role].call_tool(tool, args)
        except Exception:  # noqa: BLE001 - one transparent reconnect, then re-raise
            await self._reconnect(role)
            result = await self._clients[role].call_tool(tool, args)
        return result.data

    async def __aenter__(self) -> PersistentMcpSession:
        await self.open()
        return self

    async def __aexit__(self, *_exc) -> None:
        await self.close()
