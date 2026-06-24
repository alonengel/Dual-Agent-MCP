"""Byte-identical bonus-report serialisation + digest for the two-phase email confirm.

Both teams must emit the §9.2 report as identical bytes, exchange SHA-256 digests, and only
email when they match — a mismatch voids the bonus for both (PDF §12.2). Canonicalisation is
**sorted keys, compact separators, no whitespace** (agreed with the partner team), so field
insertion order does not matter as long as both sides hold the same keys + values.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_bytes(report: dict[str, Any]) -> bytes:
    """Deterministic serialisation: sorted keys, compact, UTF-8, no whitespace."""
    return json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(report: dict[str, Any]) -> str:
    """SHA-256 hex digest of the canonical report bytes."""
    return hashlib.sha256(canonical_bytes(report)).hexdigest()


def reports_agree(ours: dict[str, Any], theirs: dict[str, Any]) -> bool:
    """True when both teams' reports are byte-identical (safe for each to email)."""
    return digest(ours) == digest(theirs)
