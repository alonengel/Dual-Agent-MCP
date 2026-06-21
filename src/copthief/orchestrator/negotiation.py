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


def _pref(game_cfg: dict[str, Any], role: Role) -> int | None:
    """The vision radius this role advocates (only when negotiation is enabled)."""
    if not game_cfg.get("negotiable", False):
        return None
    base = int(game_cfg.get("vision_radius", 1))
    key = "cop_pref_radius" if role is Role.COP else "thief_pref_radius"
    return int(game_cfg.get(key, base))


def opening_messages(cop: Agent, thief: Agent, game_cfg: dict[str, Any]) -> dict[Role, str]:
    """Each agent emits a free-language message agreeing on (and advocating) the protocol."""
    grid = game_cfg.get("grid_size", [5, 5])
    origin = int(game_cfg.get("origin", 1))
    return {
        Role.COP: dialogue.negotiate_setup(cop.provider, Role.COP, grid, origin,
                                           _pref(game_cfg, Role.COP)),
        Role.THIEF: dialogue.negotiate_setup(thief.provider, Role.THIEF, grid, origin,
                                             _pref(game_cfg, Role.THIEF)),
    }


def negotiated_radius(game_cfg: dict[str, Any]) -> tuple[int, str]:
    """Resolve the vision radius. Inter-group: adopt it only if both roles agree,
    otherwise fall back to the base radius (an enhancement needs mutual agreement)."""
    base = int(game_cfg.get("vision_radius", 1))
    if not game_cfg.get("negotiable", False):
        return base, "base"
    cop_pref = int(game_cfg.get("cop_pref_radius", base))
    thief_pref = int(game_cfg.get("thief_pref_radius", base))
    if cop_pref == thief_pref:
        return cop_pref, "agreed"
    return base, "no-agreement"
