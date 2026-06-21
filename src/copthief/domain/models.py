"""Immutable value objects and lightweight state containers for the game."""

from __future__ import annotations

from dataclasses import dataclass, field

from copthief.constants import Action, Outcome, Role


@dataclass(frozen=True)
class Position:
    """A board cell coordinate (origin-aware values come from config)."""

    x: int
    y: int

    def shifted(self, dx: int, dy: int) -> Position:
        """Return a new position offset by (dx, dy)."""
        return Position(self.x + dx, self.y + dy)

    def as_tuple(self) -> tuple[int, int]:
        """Return the coordinate as a plain tuple for serialization."""
        return (self.x, self.y)


@dataclass(frozen=True)
class Move:
    """A single decided action: a move/stay/block plus optional target delta."""

    role: Role
    action: Action
    dx: int = 0
    dy: int = 0

    def describe(self) -> str:
        """Human-readable one-line description for logs and NL prompts."""
        if self.action is Action.BLOCK:
            return f"{self.role.value} places a barrier"
        if self.action is Action.STAY:
            return f"{self.role.value} stays in place"
        return f"{self.role.value} moves by ({self.dx},{self.dy})"


@dataclass
class SubgameResult:
    """Outcome and per-side score for one subgame."""

    index: int
    outcome: Outcome
    moves_played: int
    cop_score: int
    thief_score: int

    def to_dict(self) -> dict[str, int | str]:
        """Serialize for the JSON report."""
        return {
            "index": self.index,
            "outcome": self.outcome.value,
            "moves_played": self.moves_played,
            "cop_score": self.cop_score,
            "thief_score": self.thief_score,
        }


@dataclass
class Observation:
    """The partial view a single agent is given on its turn (DecPOMDP)."""

    role: Role
    self_pos: Position
    move_number: int
    max_moves: int
    barriers_left: int
    last_opponent_message: str = ""
    notes: list[str] = field(default_factory=list)
