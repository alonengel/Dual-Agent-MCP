"""Depth-1 minimax ("lookahead") strategy: play against the opponent's best reply.

Greedy distance play has a blind spot. A thief maximising its *current* distance can
flee into a dead end, and a cop minimising its *current* distance is easily shaken off
by one evasive step. This strategy looks a single ply ahead: it scores each candidate
move by the distance that remains *after the opponent's best reply*.

* The **cop** picks the step that stays closest once the thief flees — better
  interception, and it exploits walls/barriers that cap how far the thief can escape.
* The **thief** picks the step that stays farthest once the cop gives chase, which
  favours cells the cop cannot close on (behind a barrier or board edge); mobility and
  wall-clearance tie-breaks then keep it out of corners.

Only legal moves are considered and the cop still captures an adjacent thief, so the
game rules (PDF §4) are untouched — this is purely a stronger move policy.
"""

from __future__ import annotations

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position
from copthief.strategy.base import Strategy, chebyshev
from copthief.strategy.heuristic import HeuristicStrategy, _thief_escapes, _wall_clearance


def best_reply(opponent: Position, target: Position, board: Board, fleeing: bool) -> Position:
    """The opponent's best single-step reply: flee from / chase toward ``target``."""
    neighbours = board.free_neighbours(opponent) or [opponent]
    if fleeing:
        return max(neighbours, key=lambda n: chebyshev(n, target))
    if target in neighbours:
        return target  # the chaser steps onto the target (capture)
    return min(neighbours, key=lambda n: chebyshev(n, target))


class LookaheadStrategy(Strategy):
    """One-ply minimax: optimise the distance left after the opponent's best reply."""

    def __init__(self, use_barriers: bool = False):
        self.use_barriers = use_barriers

    def decide(self, obs: Observation, opponent: Position, board: Board) -> Move:
        """Score every legal step by the post-reply distance and take the best."""
        here = obs.self_pos
        if (self.use_barriers and obs.role is Role.COP and obs.barriers_left > 0
                and HeuristicStrategy._should_block(here, opponent, board)):
            return Move(obs.role, Action.BLOCK)

        candidates = board.free_neighbours(here)
        if not candidates:
            return Move(obs.role, Action.STAY)
        if obs.role is Role.COP and opponent in candidates:
            return _step(obs.role, here, opponent)  # capture this turn

        target = (self._best_cop(candidates, opponent, board) if obs.role is Role.COP
                  else self._best_thief(candidates, opponent, board))
        return _step(obs.role, here, target)

    @staticmethod
    def _best_cop(candidates: list[Position], thief: Position, board: Board) -> Position:
        """Minimise distance to the thief after it makes its best evasive step."""
        def score(cell: Position) -> tuple[int, int]:
            flee = best_reply(thief, cell, board, fleeing=True)
            return chebyshev(cell, flee), _thief_escapes(thief, cell, board)

        return min(candidates, key=score)

    @staticmethod
    def _best_thief(candidates: list[Position], cop: Position, board: Board) -> Position:
        """Maximise distance from the cop after it makes its best chasing step.

        The cop's own cell is excluded first: stepping onto the cop is an immediate
        self-capture, and the post-chase score is non-monotonic there (a cell *on* the
        cop scores 1, tying with far cells) — so without this guard the mobility
        tie-break could march the thief straight into the cop.
        """
        safe = [c for c in candidates if c != cop] or candidates

        def score(cell: Position) -> tuple[int, int, int]:
            chase = best_reply(cop, cell, board, fleeing=False)
            return (chebyshev(cell, chase), len(board.free_neighbours(cell)),
                    _wall_clearance(cell, board))

        return max(safe, key=score)


def _step(role: Role, here: Position, target: Position) -> Move:
    """Build a one-step MOVE from ``here`` toward an adjacent ``target`` cell."""
    return Move(role, Action.MOVE, target.x - here.x, target.y - here.y)
