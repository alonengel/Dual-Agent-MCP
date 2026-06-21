"""Tests for the opening protocol-negotiation handshake."""

from __future__ import annotations

from copthief.constants import Role
from copthief.llm.mock import MockProvider
from copthief.orchestrator.agent import Agent
from copthief.orchestrator.negotiation import opening_messages
from copthief.strategy.heuristic import HeuristicStrategy


def _agent(role: Role) -> Agent:
    return Agent(role, HeuristicStrategy(), MockProvider())


def test_opening_messages_cover_both_roles() -> None:
    messages = opening_messages(_agent(Role.COP), _agent(Role.THIEF),
                                {"grid_size": [5, 5], "origin": 1})
    assert set(messages) == {Role.COP, Role.THIEF}
    assert "cop" in messages[Role.COP].lower()
    assert "thief" in messages[Role.THIEF].lower()
