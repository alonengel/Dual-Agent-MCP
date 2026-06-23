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


def announce(provider: LLMProvider, obs: Observation, move: Move,
             disclosed: Position | None) -> str:
    """Phrase the move as free text. ``disclosed`` is the cell to reveal (the true cell,
    a decoy when deceiving, or ``None`` to keep the exact location hidden)."""
    progress = f"this is move {obs.move_number + 1} of {obs.max_moves}"
    if disclosed is not None:
        directive = (f"{move.describe()} and state plainly that you are now at "
                     f"cell ({disclosed.x},{disclosed.y}); {progress}")
    else:
        directive = (f"{move.describe()} but do not reveal your coordinates — give only a "
                     f"vague direction or a taunt; {progress}")
    user = f"ROLE: {obs.role.value}\nDIRECTIVE: {directive}\nReply with one sentence, in character."
    return provider.complete(system_for(obs.role), user)


def parse_position(text: str) -> Position | None:
    """Extract the first (x, y) coordinate mentioned in a message, if any."""
    match = _COORD.search(text)
    if not match:
        return None
    return Position(int(match.group(1)), int(match.group(2)))


def negotiate_setup(provider: LLMProvider, role: Role, grid_size: list[int], origin: int,
                    vision_pref: int | None = None) -> str:
    """Produce an opening protocol message; optionally advocate a preferred vision radius."""
    directive = (
        f"propose playing on a {grid_size[0]}x{grid_size[1]} grid with origin {origin}, "
        "turn-based with the thief moving first"
    )
    if vision_pref is not None:
        directive += f", and request a vision radius of {vision_pref} in your favour"
    directive += ", and confirm you understand the rules"
    user = f"ROLE: {role.value}\nDIRECTIVE: {directive}\nReply with one sentence."
    return provider.complete(system_for(role), user)


def intent_to_move(role: Role, action: Action, dx: int = 0, dy: int = 0) -> Move:
    """Helper to build a Move from a parsed/served intent."""
    return Move(role, action, dx, dy)
