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
from copthief.strategy.base import Strategy


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

    def decide(self, obs: Observation, board: Board, fallback_opponent: Position) -> Move:
        """Choose a move using the current belief, falling back when unknown."""
        opponent = self.belief or fallback_opponent
        return self.strategy.decide(obs, opponent, board)

    def voice(self, obs: Observation, move: Move, new_pos: Position) -> str:
        """Produce the free-text message announcing this move."""
        return dialogue.announce(self.provider, obs, move, new_pos)
