"""Tests for config, version, gatekeeper and the audit logger."""

from __future__ import annotations

import os

import pytest

from copthief.shared.config import Config, load_env
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


def test_load_env_reads_file_without_overriding_shell(tmp_path, monkeypatch) -> None:
    (tmp_path / ".env").write_text("COPTHIEF_SAMPLE=from_file\nSHELL_WINS=file\n")
    monkeypatch.setenv("SHELL_WINS", "shell")  # real env var must take priority
    assert load_env(tmp_path) is True
    assert os.environ["COPTHIEF_SAMPLE"] == "from_file"
    assert os.environ["SHELL_WINS"] == "shell"


def test_load_env_missing_file_returns_false(tmp_path) -> None:
    assert load_env(tmp_path) is False


def test_version_check_accepts_matching_minor() -> None:
    assert_config_version(__version__)


def test_version_check_rejects_mismatch() -> None:
    with pytest.raises(ValueError):
        assert_config_version("99.0.0")


def test_gatekeeper_executes_and_counts() -> None:
    gate = ApiGatekeeper({"requests_per_minute": 60, "max_retries": 2})
    assert gate.execute(lambda x: x + 1, 41) == 42
    assert gate.queue_depth() == 1


def test_gatekeeper_queue_status_reports_minute_and_hour_windows() -> None:
    gate = ApiGatekeeper({"requests_per_minute": 60, "requests_per_hour": 1000,
                          "concurrent_max": 4})
    gate.execute(lambda: None)
    status = gate.get_queue_status()
    assert status["minute_used"] == 1 and status["hour_used"] == 1
    assert status["minute_limit"] == 60 and status["hour_limit"] == 1000
    assert status["concurrent_max"] == 4


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
