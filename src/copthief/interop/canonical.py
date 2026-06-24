"""Byte-identical bonus-report serialisation + digest for the two-phase email confirm.

Both teams must emit the §9.2 report as identical bytes, exchange SHA-256 digests, and only
email when they match — a mismatch voids the bonus for both (PDF §12.2). Keys are emitted in
the report's existing (§9.2) insertion order; `build_bonus_report` already produces that order.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_bytes(report: dict[str, Any]) -> bytes:
    """Deterministic serialisation: §9.2 field order, compact, UTF-8, no trailing whitespace."""
    return json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(report: dict[str, Any]) -> str:
    """SHA-256 hex digest of the canonical report bytes."""
    return hashlib.sha256(canonical_bytes(report)).hexdigest()


def reports_agree(ours: dict[str, Any], theirs: dict[str, Any]) -> bool:
    """True when both teams' reports are byte-identical (safe for each to email)."""
    return digest(ours) == digest(theirs)
