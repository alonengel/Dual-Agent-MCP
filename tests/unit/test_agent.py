"""Tests for the Agent wrapper (belief tracking and decisions)."""

from __future__ import annotations

from copthief.constants import Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.llm.mock import MockProvider
from copthief.orchestrator.agent import Agent
from copthief.strategy.heuristic import HeuristicStrategy


def _agent(role: Role) -> Agent:
    return Agent(role, HeuristicStrategy(), MockProvider())


def test_belief_updates_from_message() -> None:
    agent = _agent(Role.COP)
    assert agent.update_belief_from("I'm at (4,4)") == Position(4, 4)
    assert agent.belief == Position(4, 4)


def test_belief_unchanged_without_coordinate() -> None:
    agent = _agent(Role.COP)
    agent.update_belief_from("nothing here")
    assert agent.belief is None


def test_decide_uses_belief_over_fallback(board: Board) -> None:
    agent = _agent(Role.COP)
    agent.update_belief_from("at (5,5)")
    obs = Observation(Role.COP, Position(1, 1), 0, 25, 5)
    move = agent.decide(obs, board, fallback_opponent=Position(1, 2))
    assert (move.dx, move.dy) == (1, 1)


def test_voice_produces_message(board: Board) -> None:
    agent = _agent(Role.THIEF)
    obs = Observation(Role.THIEF, Position(2, 2), 0, 25, 5)
    move = agent.decide(obs, board, fallback_opponent=Position(5, 5))
    text = agent.voice(obs, move, Position(2, 2))
    assert "thief" in text.lower()
