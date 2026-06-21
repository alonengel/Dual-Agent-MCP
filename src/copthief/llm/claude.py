"""Claude provider: Claude CLI first (free with a subscription), Anthropic API fallback.

Mirrors the approach used in the team's prior projects. The CLI is preferred because
it needs no API key; if the CLI is absent (e.g. CI) we fall back to the Anthropic API
using ANTHROPIC_API_KEY. Both paths satisfy the free-natural-language requirement.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile

from copthief.llm.base import LLMProvider

_log = logging.getLogger("copthief.llm.claude")
_DEFAULT_API_MODEL = "claude-sonnet-4-20250514"


class ClaudeProvider(LLMProvider):
    """Talk to Claude via the local CLI, falling back to the Anthropic HTTP API."""

    def __init__(self, model: str = "claude", temperature: float = 0.4,
                 max_tokens: int = 512, timeout: int = 120):
        super().__init__(model, temperature, max_tokens)
        self.timeout = timeout
        self._cli = shutil.which(os.environ.get("CLAUDE_CLI_PATH", "claude"))

    def complete(self, system: str, user: str) -> str:
        """Return Claude's reply, preferring the CLI and falling back to the API."""
        if self._cli:
            try:
                return self._via_cli(system, user)
            except Exception as exc:  # noqa: BLE001 - fall back to API on any CLI error
                _log.warning("Claude CLI failed (%s); trying API", exc)
        return self._via_api(system, user)

    def _via_cli(self, system: str, user: str) -> str:
        """One-shot CLI call; system prompt via temp file, user via stdin (Windows-safe)."""
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as handle:
            handle.write(system)
            sys_path = handle.name
        cmd = [self._cli, "--print", "--system-prompt-file", sys_path,
               "--output-format", "text"]
        try:
            result = subprocess.run(cmd, input=user, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace",
                                    timeout=self.timeout, check=False)
        finally:
            os.unlink(sys_path)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "Claude CLI failed")
        return result.stdout.strip()

    def _via_api(self, system: str, user: str) -> str:
        """Anthropic HTTP API fallback (requires ANTHROPIC_API_KEY)."""
        import httpx

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("no Claude CLI and ANTHROPIC_API_KEY is unset")
        model = self.model if self.model.startswith("claude") else _DEFAULT_API_MODEL
        body = {"model": model, "max_tokens": self.max_tokens, "system": system,
                "messages": [{"role": "user", "content": user}]}
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        resp = httpx.post("https://api.anthropic.com/v1/messages", json=body,
                          headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"].strip()
