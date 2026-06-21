"""Tests for the networked orchestrator's technical-loss replay (PDF section 9)."""

from __future__ import annotations

import asyncio
import random

from copthief.orchestrator.mcp_client import NetworkMatch
from copthief.shared.config import Config
from copthief.shared.logger import AuditLog


def test_valid_subgame_retries_after_technical_loss(tmp_path, monkeypatch) -> None:
    net = NetworkMatch(Config.load(), AuditLog(tmp_path, {"log_dir": "logs",
                                                          "game_log_file": "net.log"}))
    calls = {"n": 0}

    async def flaky(index: int, rng) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient network failure")
        return "scored"

    monkeypatch.setattr(net, "_run_subgame", flaky)
    result = asyncio.run(net._valid_subgame(1, random.Random(0)))
    assert result == "scored"
    assert calls["n"] == 2  # first attempt failed (void), second succeeded
