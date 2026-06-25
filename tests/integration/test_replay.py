"""Integration test: a real self-play game replays to the same outcomes from its log."""

from __future__ import annotations

from copthief.replay import replay_audit_log
from copthief.sdk import CopThiefSDK


def test_real_self_play_is_reproducible_from_its_audit_log(monkeypatch) -> None:
    monkeypatch.setenv("COPTHIEF_LLM_PROVIDER", "mock")
    sdk = CopThiefSDK(seed=5)
    sdk.audit.path.write_text("", encoding="utf-8")  # isolate this match's log
    match = sdk.run_self_play()

    summaries = replay_audit_log(sdk.audit.path, sdk.config.section("game"))
    assert len(summaries) == sdk.config.get("game.num_games")
    # Every sub-game replays through the real engine to the recorded winner.
    assert [s["outcome"] for s in summaries] == [sg["outcome"] for sg in match["sub_games"]]
