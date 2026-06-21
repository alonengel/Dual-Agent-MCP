"""Opening protocol negotiation: before play, the agents agree on the rules in
free natural language (board size, origin, turn order), as the assignment requires.

Shared by both the in-process self-play runner and the networked orchestrator so the
handshake is identical regardless of transport.
"""

from __future__ import annotations

from typing import Any

from copthief.constants import Role
from copthief.orchestrator import dialogue
from copthief.orchestrator.agent import Agent


def opening_messages(cop: Agent, thief: Agent, game_cfg: dict[str, Any]) -> dict[Role, str]:
    """Each agent emits a free-language message agreeing on the protocol."""
    grid = game_cfg.get("grid_size", [5, 5])
    origin = int(game_cfg.get("origin", 1))
    return {
        Role.COP: dialogue.negotiate_setup(cop.provider, Role.COP, grid, origin),
        Role.THIEF: dialogue.negotiate_setup(thief.provider, Role.THIEF, grid, origin),
    }
