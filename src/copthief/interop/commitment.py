"""Commit-reveal + common-state hashing for trust-minimised inter-group play.

Under partial observation a pursuer only *believes* where the evader is, and a deceptive
evader could fake or deny a capture. Each agent therefore publishes a hash **commitment** of
its own true cell every move and **reveals** it (cell + nonce) only at a capture-claim or game
end, so the terminal result is verifiable without trusting the opponent (partner protocol §A8).
"""

from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Iterable

from copthief.domain.board import Board
from copthief.domain.models import Position


def to_cell(pos: Position, board: Board) -> tuple[int, int]:
    """Map our (x, y) to the shared canonical frame: 0-based, top-left, ``(row, col)``.

    Column counts left->right; row counts top->bottom (our y increases upward, so the top
    row is the highest y). Both teams must use this same frame for commitments to match.
    """
    col = pos.x - board.origin
    row = (board.height - 1) - (pos.y - board.origin)
    return row, col


def new_nonce() -> str:
    """A fresh random nonce so identical cells produce unlinkable commitments."""
    return secrets.token_hex(16)


def commit(pos: Position, board: Board, nonce: str) -> str:
    """SHA-256 commitment binding a true cell without revealing it."""
    row, col = to_cell(pos, board)
    return hashlib.sha256(f"{row},{col}|{nonce}".encode()).hexdigest()


def verify(commitment: str, pos: Position, board: Board, nonce: str) -> bool:
    """Check a revealed cell + nonce against a previously published commitment."""
    return secrets.compare_digest(commitment, commit(pos, board, nonce))


def state_hash(barrier_cells: Iterable[tuple[int, int]], turn: str, move_count: int) -> str:
    """Common-knowledge state digest both sides recompute; a mismatch flags a desync.

    ``barrier_cells`` must already be in the canonical ``(row, col)`` frame so the two
    independent engines hash an identical payload.
    """
    payload = json.dumps(
        {"barriers": sorted(tuple(c) for c in barrier_cells), "turn": turn,
         "move_count": move_count},
        sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
