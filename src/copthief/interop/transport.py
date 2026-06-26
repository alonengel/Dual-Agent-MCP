"""Async §5.2 transport: a dumb-mailbox `deliver_message` client for inter-group play.

We **deliver** our text to the opponent's mailbox and **read our own** inbox for their turns
(each remote takes its own bearer token). Every call logs its HTTP outcome and uses a short
per-request timeout, so a stalled series self-diagnoses and a hung tunnel surfaces fast.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any
from urllib.parse import urlsplit

import httpx

from copthief.constants import Role
from copthief.shared.run_log import emit

_SKIP_NGROK = {"ngrok-skip-browser-warning": "true"}
_REPORT_SHA = re.compile(r"REPORT_SHA:([0-9a-f]{64})")
_SG = re.compile(r"^SG:(\d+)\s")  # agreed sub-game frame: "SG:<n> <taunt> || <block>"
_TIMEOUT = 30.0  # short per-request cap so a dropped/hung tunnel surfaces fast (was 120s)


def _label(url: str) -> str:
    """Compact ``host[:port]/path`` (minus the ``/mcp`` tail) for readable one-line net logs."""
    parts = urlsplit(url)
    return f"{parts.netloc}{parts.path}".removesuffix("/mcp") or url


def _client(url: str, token: str) -> Any:
    """Build a FastMCP HTTP client with bearer auth (matches our orchestrator transport)."""
    from fastmcp import Client
    from fastmcp.client.auth import BearerAuth
    from fastmcp.client.transports import StreamableHttpTransport

    auth = BearerAuth(token) if token else None
    return Client(StreamableHttpTransport(url, auth=auth, headers=_SKIP_NGROK), timeout=_TIMEOUT)


async def deliver(url: str, token: str, text: str, retries: int = 5) -> None:
    """Deliver one free-text message to the opponent's mailbox (ack only; no reply expected).

    Transient failures (5xx + connection errors) retry with exponential backoff; a 4xx re-raises
    at once. Each attempt logs its HTTP outcome so a missing turn shows which end dropped it.
    """
    label = _label(url)
    for attempt in range(retries):
        start = time.monotonic()
        try:
            async with _client(url, token) as client:
                await client.call_tool("deliver_message", {"text": text})
            emit("deliver", host=label, status="ok", latency_s=round(time.monotonic() - start, 1))
            return
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            if code < 500 or attempt == retries - 1:
                emit("deliver", host=label, status=f"HTTP {code}", outcome="giving_up")
                raise
            emit("deliver", host=label, status=f"HTTP {code}", attempt=attempt + 1, retries=retries)
        except Exception as exc:
            if attempt == retries - 1:
                emit("deliver", host=label, error=type(exc).__name__, outcome="giving_up")
                raise
            emit("deliver", host=label, error=type(exc).__name__, attempt=attempt + 1, retries=retries)
        await asyncio.sleep(min(2.0 * 2 ** attempt, 10.0))


async def read_inbox(url: str, token: str) -> list[str]:
    """Read our own server's full mailbox (opponent's delivered turns, oldest first).

    Hits our local server, so rarely fails; if it does we log the cause and re-raise."""
    try:
        async with _client(url, token) as client:
            result = await client.call_tool("inbox", {})
            data = getattr(result, "data", result)
            return list(data.get("messages", [])) if isinstance(data, dict) else []
    except Exception as exc:
        emit("recv_error", host=_label(url), error=type(exc).__name__)
        raise


async def exchange_hash(our_sha: str, opp_url: str, opp_token: str, our_url: str,
                        our_token: str, timeout: float = 90.0, poll: float = 3.0) -> str | None:
    """Two-phase confirm: deliver our report hash, then poll our inbox for theirs. Returns the
    peer's hash, or ``None`` on timeout (caller must then NOT auto-email — PDF §12.2)."""
    await deliver(opp_url, opp_token, f"REPORT_SHA:{our_sha}")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for msg in await read_inbox(our_url, our_token):
            if m := _REPORT_SHA.search(msg):
                return m.group(1)
        await asyncio.sleep(poll)
    return None


def _sg_index(msg: str) -> int | None:
    """The sub-game index stamped on a message, or ``None`` if it carries no ``SG:`` frame."""
    m = _SG.match(msg)
    return int(m.group(1)) if m else None


def _strip_sg(msg: str) -> str:
    """Drop the leading ``SG:<n>`` frame so the peer-loop sees just ``<taunt> || <block>``."""
    return _SG.sub("", msg, count=1)


def live_io(ours: dict[str, str], opp: dict[str, str], our_token: str,
            opp_tokens: dict[str, str], poll_interval: float = 1.0):
    """Build a `peer_series.io_for(index, role)` over the live mailbox: deliver to the opponent's
    opposite-role server, read our own same-role inbox, route by the ``SG:<index>`` frame — hold a
    later sub-game until we reach it, skip an earlier (stale) one, accept untagged (tolerant)."""
    consumed = {Role.COP: 0, Role.THIEF: 0}
    held = {Role.COP: {}, Role.THIEF: {}}  # role -> {sub-game index: [messages read ahead]}

    def io_for(index: int, role: Role):
        opp_role = Role.COP if role is Role.THIEF else Role.THIEF

        async def send(text: str) -> None:
            # Frame with our sub-game index so a message can't land on the wrong sub-game.
            await deliver(opp[opp_role.value], opp_tokens[opp_role.value], f"SG:{index} {text}")

        async def recv() -> str:
            if bucket := held[role].get(index):  # a message we read ahead and held for now
                return _strip_sg(bucket.pop(0))
            start, next_beat = time.monotonic(), 20.0
            while True:
                history = await read_inbox(ours[role.value], our_token)
                while consumed[role] < len(history):
                    msg = history[consumed[role]]
                    consumed[role] += 1
                    sg = _sg_index(msg)
                    if sg is None or sg == index:   # untagged (tolerant) or current -> apply
                        return _strip_sg(msg)
                    if sg > index:                  # a later sub-game -> hold until we reach it
                        held[role].setdefault(sg, []).append(msg)
                waited = time.monotonic() - start
                if waited >= next_beat:  # heartbeat so a stalled wait is visible, not silent
                    emit("recv_wait", host=_label(ours[role.value]), sub_game=index,
                         n=consumed[role] + 1, waited_s=int(waited), inbox=len(history))
                    next_beat += 20.0
                await asyncio.sleep(poll_interval)

        return send, recv

    return io_for
