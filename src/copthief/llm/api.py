"""Cloud LLM provider over HTTP for OpenAI / Anthropic / Gemini.

Keys come strictly from environment variables (never hardcoded). A single thin
HTTP client keeps the dependency surface small and the file under the line limit.
"""

from __future__ import annotations

import os

import httpx

from copthief.llm.base import LLMProvider

_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
}
_KEY_ENV = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}


class ApiProvider(LLMProvider):
    """Dispatches to a public cloud LLM API selected by ``kind``."""

    def __init__(self, model: str, kind: str = "openai", temperature: float = 0.4,
                 max_tokens: int = 512):
        super().__init__(model, temperature, max_tokens)
        self.kind = kind.lower()
        self.api_key = os.environ.get(_KEY_ENV.get(self.kind, ""), "")
        if not self.api_key:
            raise ValueError(f"missing API key env var for provider '{self.kind}'")

    def complete(self, system: str, user: str) -> str:
        """Route to the correct vendor request/response format."""
        if self.kind == "anthropic":
            return self._anthropic(system, user)
        if self.kind == "gemini":
            return self._gemini(system, user)
        return self._openai(system, user)

    def _openai(self, system: str, user: str) -> str:
        body = {"model": self.model, "temperature": self.temperature,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}]}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = self._post(_ENDPOINTS["openai"], body, headers)
        return data["choices"][0]["message"]["content"].strip()

    def _anthropic(self, system: str, user: str) -> str:
        body = {"model": self.model, "max_tokens": self.max_tokens, "system": system,
                "messages": [{"role": "user", "content": user}]}
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        data = self._post(_ENDPOINTS["anthropic"], body, headers)
        return data["content"][0]["text"].strip()

    def _gemini(self, system: str, user: str) -> str:
        url = f"{_ENDPOINTS['gemini']}/{self.model}:generateContent?key={self.api_key}"
        body = {"contents": [{"parts": [{"text": f"{system}\n\n{user}"}]}]}
        data = self._post(url, body, {})
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    @staticmethod
    def _post(url: str, body: dict, headers: dict) -> dict:
        resp = httpx.post(url, json=body, headers=headers, timeout=120)
        resp.raise_for_status()
        return resp.json()
