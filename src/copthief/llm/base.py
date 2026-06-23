"""LLM provider interface. Implementations return plain text completions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from copthief.shared.gatekeeper import ApiGatekeeper
    from copthief.shared.usage import UsageMeter


class LLMProvider(ABC):
    """A minimal text-in/text-out language-model interface.

    Public ``complete`` is a Template Method: it routes every call through the
    optional API gatekeeper (rate limiting + retries) and records token usage,
    so subclasses only implement the raw request in ``_complete``.
    """

    def __init__(self, model: str, temperature: float = 0.4, max_tokens: int = 512):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._gate: ApiGatekeeper | None = None
        self._meter: UsageMeter | None = None

    def attach(self, gatekeeper: ApiGatekeeper | None = None,
               meter: UsageMeter | None = None) -> LLMProvider:
        """Attach a shared gatekeeper and/or usage meter; returns self for chaining."""
        self._gate = gatekeeper
        self._meter = meter
        return self

    def complete(self, system: str, user: str) -> str:
        """Run the provider call through the gatekeeper and record token usage."""
        if self._gate is not None:
            result = self._gate.execute(self._complete, system, user)
        else:
            result = self._complete(system, user)
        if self._meter is not None:
            self._meter.record(self.model, f"{system}\n{user}", result)
        return result

    @abstractmethod
    def _complete(self, system: str, user: str) -> str:
        """Perform the raw model call (no rate limiting or accounting)."""

    @property
    def name(self) -> str:
        """Short provider identifier for logs and reports."""
        return f"{type(self).__name__}:{self.model}"
