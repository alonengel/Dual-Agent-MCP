"""Peer-protocol message envelopes for inter-group play (built on commitment + canonical).

Each turn an agent sends free-text prose plus three verifiable fields (the partner protocol):
a position **commitment**, the **common-state hash**, and — only at a capture-claim or game
end — a **reveal** of its true cell. These helpers build and check that envelope; the live
turn loop wires them to the remote ``deliver_message`` transport and reuses our Agent/strategy.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from copthief.domain.board import Board
from copthief.domain.models import Position
from copthief.interop import commitment


def make_envelope(prose: str, pos: Position, board: Board, nonce: str,
                  barrier_cells: Iterable[tuple[int, int]], turn: str, move_count: int,
                  reveal: bool = False) -> dict[str, Any]:
    """Build the per-move envelope: prose + commitment + common-state hash (+ optional reveal)."""
    env: dict[str, Any] = {
        "text": prose,
        "commit": commitment.commit(pos, board, nonce),
        "state_hash": commitment.state_hash(barrier_cells, turn, move_count),
    }
    if reveal:
        env["reveal"] = {"cell": list(commitment.to_cell(pos, board)), "nonce": nonce}
    return env


def state_in_sync(env: dict[str, Any], barrier_cells: Iterable[tuple[int, int]], turn: str,
                  move_count: int) -> bool:
    """True when our recomputed common-state hash matches the sender's (else a desync)."""
    return env.get("state_hash") == commitment.state_hash(barrier_cells, turn, move_count)


def confirm_capture(prior_commit: str, reveal: dict[str, Any] | None, board: Board,
                    claim_cell: Position) -> bool:
    """Verify a revealed cell against its prior commitment *and* that it equals the claim cell.

    This is how a capture is settled without a trusted referee: the pursuer claims a cell, the
    evader reveals, and the reveal must (a) match its earlier commitment and (b) be that cell.
    """
    if not reveal:
        return False
    cell = tuple(reveal["cell"])
    pos = from_cell(cell, board)
    return (commitment.verify(prior_commit, pos, board, reveal["nonce"])
            and cell == commitment.to_cell(claim_cell, board))


def from_cell(cell: tuple[int, int], board: Board) -> Position:
    """Inverse of :func:`commitment.to_cell`: canonical ``(row, col)`` -> our ``Position``."""
    row, col = cell
    return Position(col + board.origin, (board.height - 1 - row) + board.origin)
