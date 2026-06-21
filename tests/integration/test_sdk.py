"""Integration test for the SDK facade end-to-end (mock LLM)."""

from __future__ import annotations

import json

from copthief.sdk import CopThiefSDK


def test_sdk_self_play_and_report(monkeypatch) -> None:
    monkeypatch.setenv("COPTHIEF_LLM_PROVIDER", "mock")
    sdk = CopThiefSDK(seed=5)
    match = sdk.run_self_play()
    assert "totals" in match
    assert len(match["sub_games"]) == sdk.config.get("game.num_games")

    path = sdk.report_and_save(match)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["group_name"] == sdk.config.get("team.group_name")
    assert saved["totals"] == match["totals"]
