"""Tests for the LLM provider abstraction and factory (mock path, mocked api)."""

from __future__ import annotations

import pytest

from copthief.llm.factory import build_provider
from copthief.llm.mock import MockProvider


def test_mock_builds_sentence_from_directive() -> None:
    out = MockProvider().complete("sys", "ROLE: cop\nDIRECTIVE: move to (1,1)")
    assert out == "As the cop, move to (1,1)."


def test_mock_without_directive() -> None:
    out = MockProvider().complete("sys", "ROLE: thief\nhello")
    assert "thief" in out


def test_factory_default_is_mock() -> None:
    assert isinstance(build_provider({}), MockProvider)


def test_factory_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPTHIEF_LLM_PROVIDER", "mock")
    provider = build_provider({"provider": "api"})
    assert isinstance(provider, MockProvider)


def test_api_provider_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("COPTHIEF_LLM_PROVIDER", "api")
    with pytest.raises(ValueError):
        build_provider({"provider": "api", "api_kind": "openai", "model": "gpt-4o"})


def test_provider_name() -> None:
    assert "mock" in MockProvider().name
