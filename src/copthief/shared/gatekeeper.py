"""Centralized API gatekeeper: every external call (LLM, email) routes through here
so rate limits (per-minute and per-hour), retries and monitoring live in one place.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")
_log = logging.getLogger("copthief.gatekeeper")
_MINUTE = 60.0
_HOUR = 3600.0


class ApiGatekeeper:
    """Throttle (per-minute + per-hour) and retry external API calls from one place."""

    def __init__(self, limits: dict[str, Any]):
        self.rpm = int(limits.get("requests_per_minute", 30))
        self.rph = int(limits.get("requests_per_hour", self.rpm * 60))
        self.concurrent_max = int(limits.get("concurrent_max", 5))
        self.retry_after = float(limits.get("retry_after_seconds", 5))
        self.max_retries = int(limits.get("max_retries", 3))
        self._calls: deque[float] = deque()  # monotonic timestamps within the last hour

    def _wait_for_budget(self) -> None:
        """Block (queue, never drop) until both the minute and hour budgets allow a call."""
        now = time.monotonic()
        while self._calls and now - self._calls[0] > _HOUR:
            self._calls.popleft()
        within_minute = [t for t in self._calls if now - t <= _MINUTE]
        wait = 0.0
        if len(within_minute) >= self.rpm:
            wait = max(wait, _MINUTE - (now - within_minute[0]))
        if len(self._calls) >= self.rph:
            wait = max(wait, _HOUR - (now - self._calls[0]))
        if wait > 0:
            _log.warning("rate limit reached; queueing for %.1fs", wait)
            time.sleep(wait)
        self._calls.append(time.monotonic())

    def execute(self, api_call: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run an API call through throttling + bounded retries with linear backoff."""
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._wait_for_budget()
            try:
                return api_call(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - gatekeeper centralizes retry policy
                last_error = exc
                _log.warning("api call failed (attempt %d/%d): %s", attempt, self.max_retries, exc)
                time.sleep(self.retry_after * attempt)
        raise RuntimeError(f"API call failed after {self.max_retries} retries") from last_error

    def get_queue_status(self) -> dict[str, int]:
        """Report current window usage vs. configured limits (for monitoring)."""
        now = time.monotonic()
        minute_used = sum(1 for t in self._calls if now - t <= _MINUTE)
        return {"minute_used": minute_used, "minute_limit": self.rpm,
                "hour_used": len(self._calls), "hour_limit": self.rph,
                "concurrent_max": self.concurrent_max}

    def queue_depth(self) -> int:
        """Calls counted in the current minute window (back-compat helper)."""
        return self.get_queue_status()["minute_used"]
