"""Claude provider: Claude CLI first (free subscription), Anthropic API fallback.

The CLI path strips ANTHROPIC_API_KEY from its environment so Claude Code uses your
subscription (OAuth) rather than billing the API. If the CLI is missing or fails, we
fall back to the Anthropic HTTP API using ANTHROPIC_API_KEY. Both paths satisfy the
free-natural-language requirement; only the fallback consumes API credits.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess

from copthief.llm.base import LLMProvider

_log = logging.getLogger("copthief.llm.claude")
# Default to the strongest available model; messages are short so cost stays low.
_DEFAULT_API_MODEL = "claude-opus-4-8"
_DEFAULT_CLI_MODEL = "opus"  # CLI alias for the latest Opus
_ALIASES = {"opus", "sonnet", "haiku"}


class ClaudeProvider(LLMProvider):
    """Talk to Claude via the local CLI, falling back to the Anthropic HTTP API."""

    def __init__(self, model: str = "claude", temperature: float = 0.4,
                 max_tokens: int = 512, timeout: int = 120):
        # A non-Claude model (e.g. the config's Ollama default) resolves to the latest
        # Opus alias, so usage/cost accounting reflects the model actually billed.
        if not (model.startswith("claude") or model in _ALIASES):
            model = _DEFAULT_CLI_MODEL
        super().__init__(model, temperature, max_tokens)
        self.timeout = timeout
        # An empty CLAUDE_CLI_PATH (e.g. blank in .env) must fall back to "claude".
        self._cli = shutil.which(os.environ.get("CLAUDE_CLI_PATH") or "claude")

    def _complete(self, system: str, user: str) -> str:
        """Return Claude's reply, preferring the CLI and falling back to the API."""
        if self._cli:
            try:
                return self._via_cli(system, user)
            except Exception as exc:  # noqa: BLE001 - fall back to API on any CLI error
                _log.warning("Claude CLI failed (%s); trying API", exc)
        return self._via_api(system, user)

    def _cli_model(self) -> str:
        """Resolve a Claude model/alias for the CLI (defaults to latest Opus)."""
        return self.model if (self.model.startswith("claude") or self.model in _ALIASES) \
            else _DEFAULT_CLI_MODEL

    def _via_cli(self, system: str, user: str) -> str:
        """One-shot CLI call. The combined prompt goes via stdin (no unsupported flags),
        and ANTHROPIC_API_KEY is removed from the child env so Claude Code uses the
        free subscription auth instead of billing the API.
        """
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        cmd = [self._cli, "--print", "--output-format", "text", "--model", self._cli_model()]
        result = subprocess.run(cmd, input=f"{system}\n\n{user}", capture_output=True,
                                text=True, encoding="utf-8", errors="replace",
                                timeout=self.timeout, check=False, env=env)
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
