"""Belief-tracking strategy: depth-1 minimax over a Bayes-filtered opponent estimate.

Combines a probability-grid belief (:class:`BeliefGrid`) for partial observation with this
project's lookahead minimax for adversarial play. Each turn the grid is advanced and folded
with this turn's evidence, then the lookahead policy acts on the grid's most-likely cell:

* a rival within sight (Chebyshev <= ``sight_radius``) is a confirmed sighting, so belief
  **collapses to that exact cell** — no filtering noise when the truth is known;
* otherwise the grid rules out our own cell (no capture happened) and takes a soft,
  discounted nudge from the fallible believed/claimed cell.

With perfect information it tracks the truth and reduces to plain lookahead; when the rival
is unseen it pursues the highest-probability region instead of a single stale guess.
"""

from __future__ import annotations

from copthief.belief.grid import BeliefGrid
from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position
from copthief.strategy.base import Strategy, chebyshev
from copthief.strategy.lookahead import LookaheadStrategy


class BeliefStrategy(Strategy):
    """A lookahead policy that targets a Bayes-filtered belief over the opponent."""

    def __init__(self, use_barriers: bool = False, claim_discount: float = 0.4,
                 sight_radius: int = 1):
        self._look = LookaheadStrategy(use_barriers)
        self._discount = claim_discount
        self._sight = sight_radius
        self._grid: BeliefGrid | None = None

    def decide(self, obs: Observation, opponent: Position, board: Board) -> Move:
        """Advance the belief from this turn's evidence, then act on its most-likely cell."""
        if self._grid is None or obs.move_number == 0:
            self._grid = BeliefGrid(board)  # fresh prior at the start of each subgame
        else:
            self._grid.diffuse()  # the opponent has moved one ply since our last turn
        if chebyshev(obs.self_pos, opponent) <= self._sight:
            self._grid.set_point(opponent)  # within sight: collapse to the confirmed cell
        else:
            self._grid.observe_not_at(obs.self_pos)             # no capture => not on our cell
            self._grid.observe_claim(opponent, self._discount)  # fallible belief/message nudge
        return self._look.decide(obs, self._grid.most_likely(), board)

    def learn(self, reward: float) -> None:
        """Delegate the optional learning hook (no-op for this deterministic policy)."""
        self._look.learn(reward)
