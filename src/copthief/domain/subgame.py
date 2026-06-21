"""The subgame state machine: alternating turns until capture or survival."""

from __future__ import annotations

from copthief.constants import Action, Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Position
from copthief.domain.rules import Validation, validate


class Subgame:
    """Authoritative state for one pursuit round (the orchestrator is the referee)."""

    def __init__(self, board: Board, cop: Position, thief: Position, max_moves: int,
                 max_barriers: int):
        self.board = board
        self.cop = cop
        self.thief = thief
        self.max_moves = max_moves
        self.barriers_left = max_barriers
        self.move_number = 0
        self.turn: Role = Role.THIEF  # the thief moves first
        self.outcome: Outcome | None = None

    def position_of(self, role: Role) -> Position:
        """Current cell of the given role."""
        return self.cop if role is Role.COP else self.thief

    def _set_position(self, role: Role, pos: Position) -> None:
        if role is Role.COP:
            self.cop = pos
        else:
            self.thief = pos

    def captured(self) -> bool:
        """True when cop and thief occupy the same cell."""
        return self.cop == self.thief

    def apply(self, move: Move) -> Validation:
        """Validate and apply a move for the current turn, advancing the clock."""
        if self.outcome is not None:
            raise RuntimeError("subgame already finished")
        current = self.position_of(move.role)
        result = validate(move, current, self.board, self.barriers_left)
        if result.legal:
            self._commit(move, result.new_pos)
        self._advance_turn(move.role)
        self._update_outcome()
        return result

    def _commit(self, move: Move, new_pos: Position) -> None:
        """Mutate state for a legal move (movement or barrier placement)."""
        if move.action is Action.BLOCK:
            self.board.add_barrier(self.position_of(move.role))
            self.barriers_left -= 1
        elif move.action is Action.MOVE:
            self._set_position(move.role, new_pos)

    def _advance_turn(self, mover: Role) -> None:
        """Switch turn and increment the move counter after the cop has played."""
        self.turn = Role.COP if mover is Role.THIEF else Role.THIEF
        if mover is Role.COP:
            self.move_number += 1

    def _update_outcome(self) -> None:
        """Set the terminal outcome if capture happened or move budget ran out."""
        if self.captured():
            self.outcome = Outcome.COP_WIN
        elif self.move_number >= self.max_moves:
            self.outcome = Outcome.THIEF_WIN

    def finished(self) -> bool:
        """True once an outcome has been decided."""
        return self.outcome is not None
