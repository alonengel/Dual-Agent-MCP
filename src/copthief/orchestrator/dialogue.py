"""Free natural-language dialogue between agents.

The LLM *verbalises* a decided move into a sentence and *interprets* the rival's
sentence back into a believed coordinate. The protocol is intentionally not rigid:
parsing is tolerant of phrasing, which is what the assignment demands.
"""

from __future__ import annotations

import re

from copthief.constants import Action, Role
from copthief.domain.models import Move, Observation, Position
from copthief.llm.base import LLMProvider
from copthief.llm.prompts import system_for

_COORD = re.compile(r"\(?\s*(\d+)\s*[,; ]\s*(\d+)\s*\)?")


def announce(provider: LLMProvider, obs: Observation, move: Move, new_pos: Position) -> str:
    """Ask the LLM to phrase the agent's move + resulting position as free text."""
    directive = (
        f"{move.describe()} and you are now at cell ({new_pos.x},{new_pos.y}); "
        f"this is move {obs.move_number + 1} of {obs.max_moves}"
    )
    user = f"ROLE: {obs.role.value}\nDIRECTIVE: {directive}\nReply with one sentence."
    return provider.complete(system_for(obs.role), user)


def parse_position(text: str) -> Position | None:
    """Extract the first (x, y) coordinate mentioned in a message, if any."""
    match = _COORD.search(text)
    if not match:
        return None
    return Position(int(match.group(1)), int(match.group(2)))


def negotiate_setup(provider: LLMProvider, role: Role, grid_size: list[int], origin: int) -> str:
    """Produce an opening protocol-agreement message for the handshake phase."""
    directive = (
        f"propose playing on a {grid_size[0]}x{grid_size[1]} grid with origin {origin}, "
        "turn-based with the thief moving first, and confirm you understand the rules"
    )
    user = f"ROLE: {role.value}\nDIRECTIVE: {directive}\nReply with one sentence."
    return provider.complete(system_for(role), user)


def intent_to_move(role: Role, action: Action, dx: int = 0, dy: int = 0) -> Move:
    """Helper to build a Move from a parsed/served intent."""
    return Move(role, action, dx, dy)
