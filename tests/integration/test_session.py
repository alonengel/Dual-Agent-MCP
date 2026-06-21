"""Integration tests for the agent MCP session (backs the FastMCP servers)."""

from __future__ import annotations

from copthief.agents.session import AgentSession
from copthief.constants import Action, Role
from copthief.shared.config import Config


def test_session_play_turn_returns_action() -> None:
    session = AgentSession(Role.COP, Config.load())
    payload = session.play_turn(1, 1, 0, 25, 5, opponent_message="thief at (5,5)")
    assert payload["action"] in {a.value for a in Action}
    assert "message" in payload
    assert session.agent.belief is not None


def test_session_agree_protocol() -> None:
    session = AgentSession(Role.THIEF, Config.load())
    text = session.agree_protocol([5, 5], 1)
    assert "thief" in text.lower()
