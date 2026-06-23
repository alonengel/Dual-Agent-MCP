"""Factory that selects an LLM provider from config + environment override."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from copthief.llm.base import LLMProvider
from copthief.llm.mock import MockProvider
from copthief.shared.gatekeeper import ApiGatekeeper
from copthief.shared.usage import UsageMeter

if TYPE_CHECKING:
    from copthief.shared.config import Config


def build_llm_clients(config: Config) -> tuple[ApiGatekeeper, UsageMeter]:
    """Build the shared API gatekeeper (from rate_limits.json) and a usage meter."""
    services = config.rate_limits().get("rate_limits", {}).get("services", {})
    limits = services.get("llm", services.get("default", {}))
    return ApiGatekeeper(limits), UsageMeter()


def build_provider(cfg: dict[str, Any], gatekeeper: ApiGatekeeper | None = None,
                   meter: UsageMeter | None = None) -> LLMProvider:
    """Build the configured provider; env var COPTHIEF_LLM_PROVIDER wins.

    Real (network/CLI) providers are wired to the gatekeeper + meter so every
    external call is throttled, retried and metered; the offline mock is not.
    """
    provider = os.environ.get("COPTHIEF_LLM_PROVIDER", cfg.get("provider", "mock")).lower()
    model = cfg.get("model", "mock")
    temperature = float(cfg.get("temperature", 0.4))
    max_tokens = int(cfg.get("max_tokens", 512))

    if provider == "claude":
        from copthief.llm.claude import ClaudeProvider

        built: LLMProvider = ClaudeProvider(model, temperature, max_tokens)
    elif provider == "ollama":
        from copthief.llm.ollama import OllamaProvider

        built = OllamaProvider(model, temperature, max_tokens)
    elif provider == "api":
        from copthief.llm.api import ApiProvider

        built = ApiProvider(model, cfg.get("api_kind", "openai"), temperature, max_tokens)
    else:
        return MockProvider(model if model != "mock" else "mock", temperature, max_tokens)
    return built.attach(gatekeeper, meter)
