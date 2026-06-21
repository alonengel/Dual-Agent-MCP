"""Factory that selects an LLM provider from config + environment override."""

from __future__ import annotations

import os
from typing import Any

from copthief.llm.base import LLMProvider
from copthief.llm.mock import MockProvider


def build_provider(cfg: dict[str, Any]) -> LLMProvider:
    """Build the configured provider; env var COPTHIEF_LLM_PROVIDER wins."""
    provider = os.environ.get("COPTHIEF_LLM_PROVIDER", cfg.get("provider", "mock")).lower()
    model = cfg.get("model", "mock")
    temperature = float(cfg.get("temperature", 0.4))
    max_tokens = int(cfg.get("max_tokens", 512))

    if provider == "ollama":
        from copthief.llm.ollama import OllamaProvider

        return OllamaProvider(model, temperature, max_tokens)
    if provider == "api":
        from copthief.llm.api import ApiProvider

        return ApiProvider(model, cfg.get("api_kind", "openai"), temperature, max_tokens)
    return MockProvider(model if model != "mock" else "mock", temperature, max_tokens)
