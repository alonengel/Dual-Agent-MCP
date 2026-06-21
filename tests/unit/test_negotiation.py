"""Tests for the opening protocol-negotiation handshake."""

from __future__ import annotations

from copthief.constants import Role
from copthief.llm.mock import MockProvider
from copthief.orchestrator.agent import Agent
from copthief.orchestrator.negotiation import negotiated_radius, opening_messages
from copthief.strategy.heuristic import HeuristicStrategy


def _agent(role: Role) -> Agent:
    return Agent(role, HeuristicStrategy(), MockProvider())


def test_opening_messages_cover_both_roles() -> None:
    messages = opening_messages(_agent(Role.COP), _agent(Role.THIEF),
                                {"grid_size": [5, 5], "origin": 1})
    assert set(messages) == {Role.COP, Role.THIEF}
    assert "cop" in messages[Role.COP].lower()
    assert "thief" in messages[Role.THIEF].lower()


def test_agents_advocate_role_favourable_radius() -> None:
    cfg = {"grid_size": [5, 5], "origin": 1, "vision_radius": 1, "negotiable": True,
           "cop_pref_radius": 2, "thief_pref_radius": 1}
    messages = opening_messages(_agent(Role.COP), _agent(Role.THIEF), cfg)
    assert "2" in messages[Role.COP]      # cop advocates the wider radius
    assert "1" in messages[Role.THIEF]    # thief advocates the narrow radius


def test_radius_base_when_not_negotiable() -> None:
    assert negotiated_radius({"vision_radius": 1}) == (1, "base")


def test_radius_agreed_when_prefs_match() -> None:
    cfg = {"vision_radius": 1, "negotiable": True, "cop_pref_radius": 2, "thief_pref_radius": 2}
    assert negotiated_radius(cfg) == (2, "agreed")


def test_radius_falls_back_on_disagreement() -> None:
    cfg = {"vision_radius": 1, "negotiable": True, "cop_pref_radius": 2, "thief_pref_radius": 1}
    assert negotiated_radius(cfg) == (1, "no-agreement")
