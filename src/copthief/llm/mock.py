"""Deterministic offline provider so the full pipeline runs without a live LLM.

It is *not* a stub that bypasses the protocol: it produces and understands the
same free-text sentences the real providers do, which keeps tests meaningful.
"""

from __future__ import annotations

from copthief.llm.base import LLMProvider


class MockProvider(LLMProvider):
    """Generates plausible natural-language messages from embedded directives.

    The orchestrator passes a compact directive inside the user prompt (after the
    marker ``DIRECTIVE:``). The mock turns it into a fluent sentence, emulating an
    LLM verbalising an intent. Parsing back is handled by the dialogue layer.
    """

    def __init__(self, model: str = "mock", temperature: float = 0.0, max_tokens: int = 256):
        super().__init__(model, temperature, max_tokens)

    def _complete(self, system: str, user: str) -> str:
        """Echo a natural-language sentence built from the embedded directive."""
        directive = self._extract(user, "DIRECTIVE:")
        role = self._extract(user, "ROLE:") or "agent"
        if not directive:
            return f"The {role} acknowledges and is ready to proceed."
        return f"As the {role}, {directive}."

    @staticmethod
    def _extract(text: str, marker: str) -> str:
        """Return the trimmed remainder of the line following a marker."""
        for line in text.splitlines():
            if marker in line:
                return line.split(marker, 1)[1].strip()
        return ""
