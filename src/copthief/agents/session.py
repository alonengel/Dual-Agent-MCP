"""Per-agent session state backing an MCP server: belief, strategy and LLM voice."""

from __future__ import annotations

from typing import Any

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.llm.factory import build_provider
from copthief.orchestrator import dialogue
from copthief.orchestrator.agent import Agent
from copthief.strategy.factory import build_strategy


class AgentSession:
    """Holds one agent's reusable state and turns tool calls into decisions."""

    def __init__(self, role: Role, config: Any):
        self.role = role
        game = config.section("game")
        width, height = game.get("grid_size", [5, 5])
        self.board = Board(width, height, int(game.get("origin", 1)),
                           bool(game.get("diagonal_moves", True)))
        self.agent = Agent(role, build_strategy(config.section("strategy")),
                           build_provider(config.section("llm")))

    def agree_protocol(self, grid: list[int], origin: int) -> str:
        """Return this agent's protocol-handshake sentence (free text)."""
        return dialogue.negotiate_setup(self.agent.provider, self.role, grid, origin)

    def play_turn(self, self_x: int, self_y: int, move_number: int, max_moves: int,
                  barriers_left: int, opponent_message: str = "") -> dict[str, Any]:
        """Decide an action from the given observation and return action + message."""
        self.agent.update_belief_from(opponent_message)
        obs = Observation(self.role, Position(self_x, self_y), move_number, max_moves,
                          barriers_left, opponent_message)
        fallback = self.agent.belief or Position(self_x, self_y)
        move = self.agent.decide(obs, self.board, fallback)
        new_pos = Position(self_x + move.dx, self_y + move.dy)
        if move.action is not Action.MOVE:
            new_pos = Position(self_x, self_y)
        message = self.agent.voice(obs, move, new_pos)
        return {"action": move.action.value, "dx": move.dx, "dy": move.dy, "message": message}
