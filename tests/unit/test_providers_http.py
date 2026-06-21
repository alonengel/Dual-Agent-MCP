"""Tests for the HTTP-based LLM providers using mocked transport."""

from __future__ import annotations

from typing import Any

import pytest

from copthief.llm.api import ApiProvider
from copthief.llm.ollama import OllamaProvider


class _Resp:
    """Minimal stand-in for an httpx.Response."""

    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def test_ollama_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "copthief.llm.ollama.httpx.post",
        lambda *a, **k: _Resp({"message": {"content": "  hello cop  "}}),
    )
    provider = OllamaProvider("llama3.2", base_url="http://x")
    assert provider.complete("sys", "user") == "hello cop"


def test_api_openai_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(
        "copthief.llm.api.httpx.post",
        lambda *a, **k: _Resp({"choices": [{"message": {"content": "ok"}}]}),
    )
    provider = ApiProvider("gpt-4o", kind="openai")
    assert provider.complete("s", "u") == "ok"


def test_api_anthropic_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(
        "copthief.llm.api.httpx.post",
        lambda *a, **k: _Resp({"content": [{"text": "claude"}]}),
    )
    provider = ApiProvider("claude-3", kind="anthropic")
    assert provider.complete("s", "u") == "claude"


def test_api_gemini_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(
        "copthief.llm.api.httpx.post",
        lambda *a, **k: _Resp({"candidates": [{"content": {"parts": [{"text": "gem"}]}}]}),
    )
    provider = ApiProvider("gemini-1.5", kind="gemini")
    assert provider.complete("s", "u") == "gem"
