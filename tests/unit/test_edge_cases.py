"""Edge-case tests: subtle rules and boundary conditions of the pursuit game.

These pin behaviours that are easy to get wrong (and that the lecture explicitly
rewards surfacing): co-location semantics, the *symmetric* barrier rule, dead-end
traps, the capture-vs-survival tie at the move limit, and quota exhaustion.
"""

from __future__ import annotations

from copthief.constants import Action, Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Position
from copthief.domain.rules import validate
from copthief.domain.subgame import Subgame


def _game(cop: Position, thief: Position, max_moves: int = 25, max_barriers: int = 5) -> Subgame:
    return Subgame(Board(5, 5, 1, True), cop, thief, max_moves, max_barriers)


def test_thief_stepping_onto_cop_is_a_cop_win() -> None:
    # Co-location is a capture regardless of who moved last: a thief that walks into the
    # cop loses. Strong strategies never do this, but the referee must still enforce it.
    game = _game(Position(2, 2), Position(1, 1))
    game.apply(Move(Role.THIEF, Action.MOVE, 1, 1))  # thief -> (2,2), onto the cop
    assert game.captured()
    assert game.outcome is Outcome.COP_WIN


def test_barrier_blocks_the_cop_too(board: Board) -> None:
    # PDF 4.3: a barrier is impassable for BOTH agents, not only the thief.
    board.add_barrier(Position(2, 2))
    assert not validate(Move(Role.COP, Action.MOVE, 1, 1), Position(1, 1), board, 5).legal


def test_zero_displacement_move_is_illegal(board: Board) -> None:
    # A non-moving step must use STAY; a MOVE with no displacement is rejected.
    assert not validate(Move(Role.COP, Action.MOVE, 0, 0), Position(3, 3), board, 5).legal
    assert validate(Move(Role.COP, Action.STAY), Position(3, 3), board, 5).legal


def test_thief_boxed_in_by_barriers_has_no_escape() -> None:
    # Wall the thief into a corner: with every neighbour blocked it can only STAY, so
    # the cop can close in for the capture — the barrier mechanic genuinely traps.
    game = _game(Position(3, 1), Position(1, 1))
    for cell in (Position(1, 2), Position(2, 2), Position(2, 1)):
        game.board.add_barrier(cell)
    assert game.board.free_neighbours(Position(1, 1)) == []


def test_capture_on_final_move_is_cop_win_not_survival() -> None:
    # When capture and the move-limit coincide, capture wins (it is checked first).
    game = _game(Position(2, 1), Position(1, 1), max_moves=1)
    game.apply(Move(Role.THIEF, Action.STAY))       # thief stays at (1,1)
    game.apply(Move(Role.COP, Action.MOVE, -1, 0))  # cop captures on the last move
    assert game.outcome is Outcome.COP_WIN


def test_cop_exhausts_barrier_quota() -> None:
    # After placing its last barrier a further BLOCK is illegal (quota enforced).
    game = _game(Position(3, 3), Position(5, 5), max_barriers=1)
    game.apply(Move(Role.THIEF, Action.STAY))
    game.apply(Move(Role.COP, Action.BLOCK))        # consumes the only barrier
    assert game.barriers_left == 0
    illegal = validate(Move(Role.COP, Action.BLOCK), game.cop, game.board, game.barriers_left)
    assert not illegal.legal
