"""Tests for the Claude provider (CLI primary, Anthropic API fallback)."""

from __future__ import annotations

import pytest

from copthief.llm.claude import ClaudeProvider
from copthief.llm.factory import build_provider


class _Completed:
    """Stand-in for subprocess.CompletedProcess."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _Resp:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_cli_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("copthief.llm.claude.shutil.which", lambda _c: "claude")
    monkeypatch.setattr("copthief.llm.claude.subprocess.run",
                        lambda *a, **k: _Completed(0, "  As the cop, (1,2)  "))
    provider = ClaudeProvider("claude")
    assert provider.complete("sys", "user") == "As the cop, (1,2)"


def test_cli_failure_falls_back_to_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("copthief.llm.claude.shutil.which", lambda _c: "claude")
    monkeypatch.setattr("copthief.llm.claude.subprocess.run",
                        lambda *a, **k: _Completed(1, "", "cli boom"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr("httpx.post",
                        lambda *a, **k: _Resp({"content": [{"text": "api answer"}]}))
    provider = ClaudeProvider("claude-sonnet-4-20250514")
    assert provider.complete("sys", "user") == "api answer"


def test_no_cli_no_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("copthief.llm.claude.shutil.which", lambda _c: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError):
        ClaudeProvider("claude").complete("sys", "user")


def test_factory_builds_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COPTHIEF_LLM_PROVIDER", raising=False)
    monkeypatch.setattr("copthief.llm.claude.shutil.which", lambda _c: None)
    assert isinstance(build_provider({"provider": "claude"}), ClaudeProvider)
