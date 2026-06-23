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


def test_decide_uses_belief(board: Board) -> None:
    agent = _agent(Role.COP)
    agent.update_belief_from("at (5,5)")
    obs = Observation(Role.COP, Position(1, 1), 0, 25, 5)
    move = agent.decide(obs, board)
    assert (move.dx, move.dy) == (1, 1)  # steps toward the believed (5,5)


def test_blind_cop_hunts_corner(board: Board) -> None:
    agent = _agent(Role.COP)  # no belief, no last_seen → sweep toward first corner (1,1)
    obs = Observation(Role.COP, Position(3, 3), 0, 25, 5)
    move = agent.decide(obs, board)
    assert (move.dx, move.dy) == (-1, -1)


def test_blind_cop_makes_for_last_seen(board: Board) -> None:
    agent = _agent(Role.COP)
    agent.perceive(Position(2, 2), Position(5, 5), vision_radius=1)  # too far -> not seen
    agent.perceive(Position(4, 4), Position(5, 5), vision_radius=1)  # within 1 -> seen at (5,5)
    agent.belief = None  # now blind again, but remembers last_seen=(5,5)
    obs = Observation(Role.COP, Position(3, 3), 5, 25, 5)
    move = agent.decide(obs, board)
    assert (move.dx, move.dy) == (1, 1)  # heads back toward last-seen (5,5)


def test_voice_produces_message(board: Board) -> None:
    agent = _agent(Role.THIEF)
    obs = Observation(Role.THIEF, Position(2, 2), 0, 25, 5)
    move = agent.decide(obs, board)
    text = agent.voice(obs, move, Position(2, 2))
    assert "thief" in text.lower()


def test_skeptical_cop_detects_decoy() -> None:
    cop = _agent(Role.COP)
    cop.skeptical = True
    assert cop.update_belief_from("I'm at (5,5)") == Position(5, 5)  # adopt the lead
    assert not cop.belief_trusted
    cop.update_belief_from("no wait, (1,1)")  # a second claim is ignored while unverified
    assert cop.belief == Position(5, 5)
    # arrive at the claimed cell, nobody in sight -> recognise the lie, distrust further claims
    assert cop.perceive(Position(5, 5), Position(1, 1), vision_radius=1) is False
    assert cop.belief is None and cop.trust_claims is False
    cop.update_belief_from("really, I'm at (2,2)")  # the proven liar is now ignored
    assert cop.belief is None


def test_reset_restores_trust_and_clears_state() -> None:
    cop = _agent(Role.COP)
    cop.skeptical = True
    cop.trust_claims = False
    cop.belief = Position(3, 3)
    cop.last_seen = Position(4, 4)
    cop.reset()
    assert cop.trust_claims and cop.belief is None and cop.last_seen is None
