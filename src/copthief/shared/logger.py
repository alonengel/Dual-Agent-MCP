"""Logging setup. The lecture stresses this repeatedly: a state-by-state audit log
is mandatory and exists specifically to resolve disputes between groups.

Two channels are provided:
  * a standard human/console + rotating debug file logger, and
  * an append-only JSON-lines *audit* log capturing every game event.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_AUDIT_LOGGER_NAME = "copthief.audit"


def setup_logging(root: Path, cfg: dict[str, Any]) -> logging.Logger:
    """Configure root logging from logging_config.json values; return app logger."""
    log_dir = root / cfg.get("log_dir", "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, str(cfg.get("level", "INFO")).upper(), logging.INFO)

    logger = logging.getLogger("copthief")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:  # idempotent across repeated calls (tests, reruns)
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    if cfg.get("console", True):
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(fmt)
        logger.addHandler(console)

    file_handler = logging.FileHandler(log_dir / "copthief.log", encoding="utf-8")
    file_handler.setLevel(getattr(logging, str(cfg.get("file_level", "DEBUG")).upper()))
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    return logger


class AuditLog:
    """Append-only structured event log: the evidence trail for dispute resolution."""

    def __init__(self, root: Path, cfg: dict[str, Any]):
        log_dir = root / cfg.get("log_dir", "logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        self.path = log_dir / cfg.get("game_log_file", "game_audit.log")
        self._logger = logging.getLogger(_AUDIT_LOGGER_NAME)

    def record(self, event: str, **fields: Any) -> dict[str, Any]:
        """Write one immutable audit line and return the recorded entry."""
        entry = {"ts": datetime.now(UTC).isoformat(), "event": event, **fields}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._logger.debug("audit:%s %s", event, fields)
        return entry
