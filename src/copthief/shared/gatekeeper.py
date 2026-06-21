"""Centralized API gatekeeper: every external call (LLM, email) routes through here
so rate limits, retries and monitoring are enforced in one place.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")
_log = logging.getLogger("copthief.gatekeeper")


class ApiGatekeeper:
    """Throttle and retry external API calls based on a rate-limit config."""

    def __init__(self, limits: dict[str, Any]):
        self.rpm = int(limits.get("requests_per_minute", 30))
        self.retry_after = float(limits.get("retry_after_seconds", 5))
        self.max_retries = int(limits.get("max_retries", 3))
        self._calls: deque[float] = deque()

    def _throttle(self) -> None:
        """Block until the trailing-60s request budget allows another call."""
        now = time.monotonic()
        while self._calls and now - self._calls[0] > 60:
            self._calls.popleft()
        if len(self._calls) >= self.rpm:
            sleep_for = 60 - (now - self._calls[0])
            _log.warning("rate limit reached; queueing for %.1fs", sleep_for)
            time.sleep(max(sleep_for, 0))
        self._calls.append(time.monotonic())

    def execute(self, api_call: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Run an API call through throttling + bounded retries with backoff."""
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            try:
                return api_call(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - gatekeeper centralizes retry policy
                last_error = exc
                _log.warning("api call failed (attempt %d/%d): %s", attempt, self.max_retries, exc)
                time.sleep(self.retry_after * attempt)
        raise RuntimeError(f"API call failed after {self.max_retries} retries") from last_error

    def queue_depth(self) -> int:
        """Return the number of calls counted in the current rate window."""
        return len(self._calls)
