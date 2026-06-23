"""Local Ollama provider (HTTP). Used when COPTHIEF_LLM_PROVIDER=ollama."""

from __future__ import annotations

import os

import httpx

from copthief.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Calls a locally running Ollama server's chat endpoint."""

    def __init__(self, model: str, temperature: float = 0.4, max_tokens: int = 512,
                 base_url: str | None = None):
        super().__init__(model, temperature, max_tokens)
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    def _complete(self, system: str, user: str) -> str:
        """Send a chat request to Ollama and return the assistant content."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        resp = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
