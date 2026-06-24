"""Per-agent server state backing the MCP tools.

Per PDF section 5.2, the MCP server holds **no LLM and no strategy** — it only
exposes pure tools that operate on this agent's local view of the world (its
position, remaining barriers, and the messages it has been told). All intelligence
(LLM dialogue + move decisions) lives in the MCP client (the orchestrator).
"""

from __future__ import annotations

from typing import Any

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Position
from copthief.domain.rules import validate


class AgentSession:
    """Holds one agent's local state and exposes pure, LLM-free tool operations."""

    def __init__(self, role: Role, config: Any):
        game = config.section("game")
        width, height = game.get("grid_size", [5, 5])
        self.role = role
        self.board = Board(width, height, int(game.get("origin", 1)),
                           bool(game.get("diagonal_moves", True)))
        self.max_moves = int(game.get("max_moves", 25))
        self.barriers_left = int(game.get("max_barriers", 5))
        self.pos = Position(self.board.origin, self.board.origin)
        self.history: list[str] = []

    def reset(self, x: int, y: int, barriers_left: int) -> dict[str, Any]:
        """Start a new subgame: place this agent and clear its memory."""
        self.pos = Position(x, y)
        self.barriers_left = barriers_left
        self.history = []
        return self.observe()

    def observe(self) -> dict[str, Any]:
        """Return this agent's partial view (its own cell, barriers, recent messages)."""
        return {"role": self.role.value, "x": self.pos.x, "y": self.pos.y,
                "barriers_left": self.barriers_left, "history": self.history[-5:]}

    def move(self, dx: int, dy: int) -> dict[str, Any]:
        """Execute a one-step move on this agent's local state."""
        result = validate(Move(self.role, Action.MOVE, dx, dy), self.pos,
                          self.board, self.barriers_left)
        if result.legal:
            self.pos = result.new_pos
        return {"x": self.pos.x, "y": self.pos.y, "legal": result.legal, "reason": result.reason}

    def place_barrier(self) -> dict[str, Any]:
        """Cop-only: drop a barrier on the current cell (no movement)."""
        result = validate(Move(self.role, Action.BLOCK), self.pos, self.board,
                          self.barriers_left)
        if result.legal:
            self.board.add_barrier(self.pos)
            self.barriers_left -= 1
        return {"legal": result.legal, "reason": result.reason,
                "barriers_left": self.barriers_left}

    def deliver_message(self, text: str) -> dict[str, Any]:
        """Free-text cross-agent channel (the inter-group peer protocol's tool). The server
        only records the message; the LLM that interprets it lives in the client (PDF §5.2)."""
        self.history.append(text)
        return {"ok": True, "count": len(self.history)}

    def note(self, message: str) -> dict[str, Any]:
        """Alias for the internal orchestrator path; see :meth:`deliver_message`."""
        return self.deliver_message(message)
