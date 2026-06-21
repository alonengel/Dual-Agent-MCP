"""An agent: a role-bound bundle of strategy, LLM voice and a belief about the rival.

The agent is deliberately thin — it decides a move via its strategy, verbalises it
through the LLM, and updates its belief from the opponent's free-text message.
"""

from __future__ import annotations

from copthief.constants import Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Observation, Position
from copthief.llm.base import LLMProvider
from copthief.orchestrator import dialogue
from copthief.strategy.base import Strategy, chebyshev


class Agent:
    """Wraps one side's decision-making and natural-language communication."""

    def __init__(self, role: Role, strategy: Strategy, provider: LLMProvider):
        self.role = role
        self.strategy = strategy
        self.provider = provider
        self.belief: Position | None = None

    def update_belief_from(self, message: str) -> Position | None:
        """Parse the opponent's message into a believed position (if present)."""
        parsed = dialogue.parse_position(message)
        if parsed is not None:
            self.belief = parsed
        return self.belief

    def perceive(self, self_pos: Position, opponent_true: Position, vision_radius: int) -> bool:
        """Acquire the opponent's exact cell when within vision; drop a stale lead else.

        Returns True if the opponent is currently visible (ground truth acquired).
        """
        if chebyshev(self_pos, opponent_true) <= vision_radius:
            self.belief = opponent_true
            return True
        if self.belief is not None and self_pos == self.belief:
            self.belief = None  # reached the last-known cell but the target is not here
        return False

    def decide(self, obs: Observation, board: Board, fallback_opponent: Position) -> Move:
        """Choose a move using the current belief, falling back when unknown."""
        opponent = self.belief or fallback_opponent
        return self.strategy.decide(obs, opponent, board)

    def voice(self, obs: Observation, move: Move, disclosed: Position | None) -> str:
        """Produce the free-text message; ``disclosed`` is the cell to reveal (or None)."""
        return dialogue.announce(self.provider, obs, move, disclosed)
