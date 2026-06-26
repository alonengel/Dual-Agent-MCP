"""Timestamped, structured run-log for the live inter-group bonus series (PDF §9 evidence).

The series runner historically ``print()``-ed bare ``[series]/[ply]/[deliver]`` lines with no
timestamps, so the captured stdout could not be correlated in time with the opponent's audit
trail. This thin helper keeps a human-readable console echo but **prepends an ISO-8601 UTC
timestamp** and mirrors every event into an append-only JSON-lines file using the same
``{"ts", "event", ...}`` schema as :class:`copthief.shared.logger.AuditLog` — so future runs are
self-evidencing instead of needing timestamps reconstructed after the fact.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RunLog:
    """Append-only JSON-lines event file plus an optional timestamped console echo."""

    def __init__(self, path: Path, echo: bool = True) -> None:
        self.path = path
        self.echo = echo
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, *, msg: str | None = None, **fields: Any) -> dict[str, Any]:
        """Record one event: append ``{ts, event, ...}`` JSON and echo a timestamped line.

        ``msg`` overrides the console tail (e.g. to show a turn's free-text taunt); when omitted
        the tail is rendered from ``fields`` so structured-only call sites still read cleanly.
        """
        ts = datetime.now(UTC).isoformat()
        entry = {"ts": ts, "event": event, **fields}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if self.echo:
            tail = msg if msg is not None else " ".join(f"{k}={v}" for k, v in fields.items())
            print(f"{ts} | {event} | {tail}", flush=True)
        return entry


_default = RunLog(Path("logs") / "bonus_series.log")


def emit(event: str, *, msg: str | None = None, **fields: Any) -> dict[str, Any]:
    """Module-level convenience over the default :class:`RunLog` (``logs/bonus_series.log``)."""
    return _default.emit(event, msg=msg, **fields)
