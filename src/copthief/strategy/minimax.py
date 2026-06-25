"""Depth-limited minimax: the depth-1 ``lookahead`` generalised to full game-tree search.

The ``lookahead`` policy optimises the distance left after the opponent's *single* best reply.
That one-ply horizon beats greedy play but still misses multi-step cornering: on the 5x5 /
4-round benchmark an optimal pursuer can force capture from *every* start, yet depth-1 realises
only ~0.65 of it (and the learned linear policy ~0.79). This strategy searches ``depth`` plies of
alternating cop/thief play — capture is a terminal win (sooner is better), exhausting the move
budget is a terminal loss — and at the horizon falls back to Chebyshev distance. With enough
depth it *solves* the benchmark: capture from every start against every thief (README §9.1).

A single cop-perspective value drives both roles: the cop **maximises** it (seek capture), the
thief **minimises** it (run out the clock). Turn order and the move counter mirror the engine
exactly (thief first; the counter ticks after the cop's ply). A per-decide transposition table
keeps the 5x5 search well under a millisecond per move.
"""

from __future__ import annotations

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position
from copthief.strategy.base import Strategy, chebyshev

_WIN = 1000.0  # capture payoff (cop-positive); dwarfs any distance term at the leaf


class MinimaxStrategy(Strategy):
    """Depth-``d`` minimax over alternating moves; cop maximises value, thief minimises it."""

    def __init__(self, depth: int = 8):
        self.depth = max(1, depth)

    def decide(self, obs: Observation, opponent: Position, board: Board) -> Move:
        """Search ``depth`` plies and step toward the best-valued move for this role."""
        here = obs.self_pos
        is_cop = obs.role is Role.COP
        neighbours = board.free_neighbours(here)
        if is_cop and opponent in neighbours:
            return _step(obs.role, here, opponent)  # capture available this turn
        candidates = (neighbours or []) + [here]  # STAY is always a legal fallback
        value = _searcher(board, obs.max_moves, self.depth)

        def score(cell: Position) -> float:
            # Evaluate the state *after* our ply: the cop advances the clock and yields to the
            # thief; the thief keeps the clock and yields to the cop.
            if is_cop:
                return value(cell.as_tuple(), opponent.as_tuple(), obs.move_number + 1, False)
            return value(opponent.as_tuple(), cell.as_tuple(), obs.move_number, True)

        pick = (max if is_cop else min)(candidates, key=score)
        return Move(obs.role, Action.STAY) if pick == here else _step(obs.role, here, pick)


def _searcher(board: Board, max_moves: int, depth: int):
    """Build a memoised cop-perspective minimax value function over the given board/clock."""
    memo: dict = {}

    def nbrs(p: Position) -> list[Position]:
        return (board.free_neighbours(p) or []) + [p]  # include STAY

    def value(cop: tuple, thief: tuple, mn: int, cop_turn: bool, d: int = depth - 1) -> float:
        if cop == thief:
            return _WIN - mn               # captured — fewer moves is better
        if mn >= max_moves:
            return -_WIN                    # thief survived the move budget
        if d == 0:
            return float(-chebyshev(Position(*cop), Position(*thief)))
        key = (cop, thief, mn, cop_turn, d)
        if key not in memo:
            if cop_turn:
                memo[key] = max(value(n.as_tuple(), thief, mn + 1, False, d - 1)
                                for n in nbrs(Position(*cop)))
            else:
                memo[key] = min(value(cop, n.as_tuple(), mn, True, d - 1)
                                for n in nbrs(Position(*thief)))
        return memo[key]

    return value


def _step(role: Role, here: Position, target: Position) -> Move:
    """One-step MOVE from ``here`` to an adjacent ``target`` cell."""
    return Move(role, Action.MOVE, target.x - here.x, target.y - here.y)
