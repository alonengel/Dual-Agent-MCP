"""Tests for config, version, gatekeeper and the audit logger."""

from __future__ import annotations

import pytest

from copthief.shared.config import Config
from copthief.shared.gatekeeper import ApiGatekeeper
from copthief.shared.logger import AuditLog
from copthief.shared.version import __version__, assert_config_version


def test_config_loads_game_section() -> None:
    cfg = Config.load()
    assert cfg.get("game.max_moves") == 25
    assert cfg.section("scoring")["cop_win"] == 20


def test_config_missing_key_returns_default() -> None:
    cfg = Config.load()
    assert cfg.get("nope.missing", "fallback") == "fallback"


def test_version_check_accepts_matching_minor() -> None:
    assert_config_version(__version__)


def test_version_check_rejects_mismatch() -> None:
    with pytest.raises(ValueError):
        assert_config_version("99.0.0")


def test_gatekeeper_executes_and_counts() -> None:
    gate = ApiGatekeeper({"requests_per_minute": 60, "max_retries": 2})
    assert gate.execute(lambda x: x + 1, 41) == 42
    assert gate.queue_depth() == 1


def test_gatekeeper_retries_then_raises() -> None:
    gate = ApiGatekeeper({"requests_per_minute": 60, "retry_after_seconds": 0, "max_retries": 2})
    calls = {"n": 0}

    def boom() -> None:
        calls["n"] += 1
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        gate.execute(boom)
    assert calls["n"] == 2


def test_audit_log_records_lines(tmp_path) -> None:
    audit = AuditLog(tmp_path, {"log_dir": "logs", "game_log_file": "a.log"})
    entry = audit.record("turn", index=1, move=2)
    assert entry["event"] == "turn"
    assert audit.path.exists()
    assert audit.path.read_text(encoding="utf-8").count("\n") == 1
