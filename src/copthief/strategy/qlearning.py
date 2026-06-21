"""Tabular Q-learning strategy (epsilon-greedy + Bellman update).

This mirrors the minimal Q-table example from the assignment. State is the
clipped relative position of the opponent; actions are the legal step directions.
"""

from __future__ import annotations

import random

import numpy as np

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position
from copthief.strategy.base import Strategy

_REL = 3  # relative-coordinate clip: dx,dy in [-_REL, _REL] -> 7 buckets each


class QTableStrategy(Strategy):
    """Learns action values online via the Bellman equation."""

    def __init__(self, learning_rate: float, discount_factor: float, epsilon: float,
                 rng: random.Random | None = None):
        self.alpha = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.rng = rng or random.Random()
        self.directions = ((0, 1), (0, -1), (1, 0), (-1, 0),
                           (1, 1), (1, -1), (-1, 1), (-1, -1))
        self.q = np.zeros(((2 * _REL + 1) ** 2, len(self.directions)))
        self._last: tuple[int, int] | None = None

    def _state_index(self, here: Position, opponent: Position) -> int:
        """Encode clipped relative opponent offset into a flat state index."""
        dx = max(-_REL, min(_REL, opponent.x - here.x)) + _REL
        dy = max(-_REL, min(_REL, opponent.y - here.y)) + _REL
        return dx * (2 * _REL + 1) + dy

    def decide(self, obs: Observation, opponent: Position, board: Board) -> Move:
        """Choose a direction epsilon-greedily, biased to legal cells."""
        here = obs.self_pos
        state = self._state_index(here, opponent)
        order = list(range(len(self.directions)))
        if self.rng.random() >= self.epsilon:
            order.sort(key=lambda a: self.q[state, a], reverse=True)
        else:
            self.rng.shuffle(order)
        for action in order:
            dx, dy = self.directions[action]
            if board.is_free(here.shifted(dx, dy)):
                self._last = (state, action)
                return Move(obs.role, Action.MOVE, dx, dy)
        self._last = (state, order[0])
        return Move(obs.role, Action.STAY)

    def learn(self, reward: float) -> None:
        """Apply the Bellman update for the most recent (state, action)."""
        if self._last is None:
            return
        state, action = self._last
        best_next = float(np.max(self.q[state]))
        td_target = reward + self.gamma * best_next
        self.q[state, action] += self.alpha * (td_target - self.q[state, action])


def shaped_reward(role: Role, before: int, after: int, captured: bool) -> float:
    """Distance-shaped reward: cop rewarded for closing in, thief for fleeing."""
    if captured:
        return 10.0 if role is Role.COP else -10.0
    delta = after - before
    return float(-delta if role is Role.COP else delta)
