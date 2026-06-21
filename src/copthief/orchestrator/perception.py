"""Partial-observation helpers shared by the self-play and networked orchestrators.

Implements the DecPOMDP observation model the PDF describes (section 4.5's "vision
radius"): an agent only knows the opponent's exact cell when within the radius; beyond
it, it relies on free-text messages, which under 'partial' disclosure omit coordinates
(or, with deception enabled, may state a false one).
"""

from __future__ import annotations

import random

from copthief.domain.board import Board
from copthief.domain.models import Position
from copthief.orchestrator.agent import Agent
from copthief.strategy.base import chebyshev


def center(board: Board) -> Position:
    """The board centre — a reasonable search target when the trail goes cold."""
    return Position(board.origin + board.width // 2, board.origin + board.height // 2)


def should_reveal(new_pos: Position, opponent_true: Position, radius: int, exact: bool) -> bool:
    """Reveal exact coordinates only when the opponent can already see you (or in exact mode)."""
    return exact or chebyshev(new_pos, opponent_true) <= radius


def disclosed_cell(new_pos: Position, opponent_true: Position, radius: int, exact: bool,
                   deception: bool, board: Board, rng: random.Random) -> Position | None:
    """Decide which cell (if any) to reveal: the truth, a decoy, or nothing."""
    if should_reveal(new_pos, opponent_true, radius, exact):
        return new_pos
    if deception:
        return _decoy(board, rng, new_pos)
    return None


def relay(opponent: Agent, mover_pos: Position, opponent_true: Position, radius: int,
          message: str) -> None:
    """Update the opponent's belief: ground truth if it can see the mover, else from text."""
    if chebyshev(opponent_true, mover_pos) <= radius:
        opponent.belief = mover_pos
    else:
        opponent.update_belief_from(message)


def _decoy(board: Board, rng: random.Random, true_pos: Position) -> Position:
    """Pick a random in-bounds cell other than the true one (a believable lie)."""
    cells = [Position(x, y)
             for x in range(board.origin, board.origin + board.width)
             for y in range(board.origin, board.origin + board.height)
             if Position(x, y) != true_pos]
    return rng.choice(cells)
