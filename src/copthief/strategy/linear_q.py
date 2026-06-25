"""Linear-function-approximation value learning over afterstate features.

Instead of a per-state table, the value of moving to a cell is ``w · φ(afterstate)``, where
``φ`` captures the quantities that actually drive pursuit/evasion — distance to the rival, the
rival's remaining escape cells, own mobility, how boxed-in the rival is (wall proximity), and
capture/adjacency flags. Because the weights generalise across *all* positions, the policy can
learn cornering (push the rival toward walls, cut its escapes) that a relative-offset table
cannot represent — without needing every state visited.

Weights are learned by **Monte-Carlo** return (update each visited afterstate toward the
realised discounted return at episode end), not bootstrapped TD: linear function approximation
with bootstrapping + the off-policy max is the classic "deadly triad" and diverges here, while
MC is stable. The mover greedily picks the highest-valued legal afterstate (ε-greedy); the
trainer keeps one instance per role, so the same features serve cop and thief with
opposite-signed weights.
"""

from __future__ import annotations

import random

import numpy as np

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position
from copthief.strategy.base import Strategy, chebyshev
from copthief.strategy.heuristic import _wall_clearance
from copthief.strategy.lookahead import best_reply

_FEATURES = ("bias", "distance", "opp_escapes", "own_mobility", "opp_wall", "capture",
             "adjacent", "post_reply")


class LinearQStrategy(Strategy):
    """Afterstate linear Q-learning: value a move by ``w · φ(resulting position)``."""

    def __init__(self, learning_rate: float, discount_factor: float, epsilon: float,
                 rng: random.Random | None = None):
        self.alpha = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.rng = rng or random.Random()
        self.weights = np.zeros(len(_FEATURES))
        self._last_phi: np.ndarray | None = None
        self._episode: list[tuple[np.ndarray, float]] = []  # (chosen φ, reward) per ply

    def _features(self, cell: Position, opponent: Position, board: Board,
                  role: Role) -> np.ndarray:
        """Normalised afterstate features for ``role`` ending on ``cell`` (rival at ``opponent``)."""
        span = max(board.width, board.height) - 1 or 1
        opp_neighbours = board.free_neighbours(opponent)
        # The rival's best one-step reply: it flees a cop and chases a thief. The distance that
        # then remains is exactly the depth-1 lookahead objective — handed to the learner as a
        # feature so a linear policy can approximate the minimax.
        reply = best_reply(opponent, cell, board, fleeing=role is Role.COP)
        return np.array([
            1.0,
            chebyshev(cell, opponent) / span,                              # distance to rival
            sum(1 for n in opp_neighbours if n != cell) / 8.0,            # rival escape cells
            len(board.free_neighbours(cell)) / 8.0,                       # own mobility
            _wall_clearance(opponent, board) / span,                      # rival wall clearance
            1.0 if cell == opponent else 0.0,                            # capture / co-location
            1.0 if chebyshev(cell, opponent) == 1 else 0.0,              # adjacency
            chebyshev(cell, reply) / span,                               # post-reply distance
        ])

    def decide(self, obs: Observation, opponent: Position, board: Board) -> Move:
        """Pick the legal afterstate with the highest value (ε-greedy); record φ for learning."""
        here = obs.self_pos
        cells = board.free_neighbours(here) or [here]  # STAY when boxed in
        phis = [self._features(c, opponent, board, obs.role) for c in cells]
        if self.rng.random() >= self.epsilon:
            idx = max(range(len(cells)), key=lambda i: float(self.weights @ phis[i]))
        else:
            idx = self.rng.randrange(len(cells))
        self._last_phi = phis[idx]
        cell = cells[idx]
        if cell == here:
            return Move(obs.role, Action.STAY)
        return Move(obs.role, Action.MOVE, cell.x - here.x, cell.y - here.y)

    def learn(self, reward: float) -> None:
        """Buffer (chosen afterstate, reward) for the Monte-Carlo update at episode end."""
        if self._last_phi is not None:
            self._episode.append((self._last_phi, reward))

    def end_episode(self) -> None:
        """Update weights toward the realised discounted return of each visited afterstate."""
        ret = 0.0
        for phi, reward in reversed(self._episode):
            ret = reward + self.gamma * ret
            self.weights += self.alpha * (ret - float(self.weights @ phi)) * phi
        self._episode.clear()
        self._last_phi = None
