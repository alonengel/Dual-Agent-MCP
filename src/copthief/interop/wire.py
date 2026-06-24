"""Embed/extract the agreed inter-group move block inside the free-text channel.

The channel carries prose only, but the four fields below are *exact* values an LLM can't
reliably copy, so each turn appends one verbatim block after the prose; the receiver pulls it out
with a tolerant regex. Format agreed byte-for-byte with the partner team (group ImreEyal):

    MOVE:[row,col] | COMMIT:<sha256> | NONCE:<nonce> | STATE:<sha256>

``MOVE`` is the mover's new cell in the canonical 0-based top-left ``[row,col]`` frame; ``COMMIT``
binds it (``SHA-256(canonical{nonce,pos})``); ``NONCE`` opens the commit (per-mover length); and
``STATE`` is the common-state hash computed *after* the mover's ply. Under full disclosure
(Option A) the cleartext ``MOVE`` is the truth and ``COMMIT``+``NONCE`` are a per-ply audit.
"""

from __future__ import annotations

import re

_HEX = r"[0-9a-f]{64}"
_BLOCK = re.compile(
    rf"MOVE:\[\s*(\d+)\s*,\s*(\d+)\s*\]\s*\|\s*COMMIT:({_HEX})"
    rf"\s*\|\s*NONCE:(\S+?)\s*\|\s*STATE:({_HEX})"
)


def encode(prose: str, cell: tuple[int, int], commit: str, nonce: str, state: str) -> str:
    """Append the verbatim move block to a free-text message, on a single clean line.

    The LLM taunt is flattened (any newline/tab/run collapsed to one space) and its ``|`` is
    neutralised, so the move block always stays on line 1 with the only ``|`` being its own field
    separators. This stops a line-based or ``|``-splitting peer parser from ever misreading an
    opener as "no move" (which previously made the partner skip our sub-game openers)."""
    row, col = cell
    flat = " ".join(prose.split()).replace("|", "/")
    return f"{flat} || MOVE:[{row},{col}] | COMMIT:{commit} | NONCE:{nonce} | STATE:{state}"


def decode(text: str) -> dict | None:
    """Pull the move block out of an incoming message; ``None`` if no well-formed block is found."""
    m = _BLOCK.search(text)
    if not m:
        return None
    return {
        "cell": (int(m.group(1)), int(m.group(2))),
        "commit": m.group(3),
        "nonce": m.group(4),
        "state": m.group(5),
    }
