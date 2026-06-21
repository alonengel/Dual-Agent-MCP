"""LLM provider interface. Implementations return plain text completions."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """A minimal text-in/text-out language-model interface."""

    def __init__(self, model: str, temperature: float = 0.4, max_tokens: int = 512):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return the model's text completion for a system+user prompt pair."""

    @property
    def name(self) -> str:
        """Short provider identifier for logs and reports."""
        return f"{type(self).__name__}:{self.model}"
