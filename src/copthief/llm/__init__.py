"""LLM provider abstraction used for the free natural-language dialogue.

Providers: ``mock`` (offline, deterministic — default for tests/CI),
``ollama`` (local model) and ``api`` (OpenAI / Anthropic / Gemini cloud).
"""

from copthief.llm.base import LLMProvider
from copthief.llm.factory import build_provider

__all__ = ["LLMProvider", "build_provider"]
