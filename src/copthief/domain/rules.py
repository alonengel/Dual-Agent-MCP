"""Move legality rules, kept separate from state mutation for testability."""

from __future__ import annotations

from dataclasses import dataclass

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Position


@dataclass
class Validation:
    """Result of checking a proposed move: legality, reason, resulting cell."""

    legal: bool
    reason: str
    new_pos: Position


def _step_in_range(move: Move, diagonal: bool) -> bool:
    """A move may shift at most one cell (and diagonals only when enabled)."""
    if abs(move.dx) > 1 or abs(move.dy) > 1:
        return False
    if not diagonal and move.dx != 0 and move.dy != 0:
        return False
    return not (move.dx == 0 and move.dy == 0)


def validate(move: Move, current: Position, board: Board, barriers_left: int) -> Validation:
    """Validate a move for the given role against board and barrier limits."""
    if move.action is Action.BLOCK:
        if move.role is not Role.COP:
            return Validation(False, "only the cop may place barriers", current)
        if barriers_left <= 0:
            return Validation(False, "no barriers remaining", current)
        return Validation(True, "barrier placed; actor stays put", current)

    if move.action is Action.STAY:
        return Validation(True, "stay", current)

    if not _step_in_range(move, board.diagonal):
        return Validation(False, "move exceeds one step or illegal diagonal", current)

    target = current.shifted(move.dx, move.dy)
    if not board.in_bounds(target):
        return Validation(False, "target off board", current)
    if board.is_barrier(target):
        # PDF 4.3: a barrier is impassable for both agents, like a wall or board edge,
        # so the move is rejected (the actor stays) rather than being committed.
        return Validation(False, "target cell is a barrier", target)
    return Validation(True, "ok", target)
