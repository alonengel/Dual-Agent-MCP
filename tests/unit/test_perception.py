"""Tests for partial-observation perception helpers and agent vision."""

from __future__ import annotations

import random

from copthief.constants import Role
from copthief.domain.board import Board
from copthief.domain.models import Position
from copthief.llm.mock import MockProvider
from copthief.orchestrator import perception
from copthief.orchestrator.agent import Agent
from copthief.strategy.heuristic import HeuristicStrategy


def _agent(role: Role) -> Agent:
    return Agent(role, HeuristicStrategy(), MockProvider())


def test_center_of_board() -> None:
    assert perception.center(Board(5, 5, origin=1)) == Position(3, 3)


def test_should_reveal_within_radius() -> None:
    assert perception.should_reveal(Position(1, 1), Position(2, 2), radius=2, exact=False)
    assert not perception.should_reveal(Position(1, 1), Position(5, 5), radius=2, exact=False)
    assert perception.should_reveal(Position(1, 1), Position(5, 5), radius=2, exact=True)


def test_disclosed_cell_truth_hidden_and_decoy() -> None:
    board = Board(5, 5, origin=1)
    rng = random.Random(0)
    here, far = Position(1, 1), Position(5, 5)
    assert perception.disclosed_cell(here, Position(2, 2), 2, False, False, board, rng) == here
    assert perception.disclosed_cell(here, far, 2, False, False, board, rng) is None
    decoy = perception.disclosed_cell(here, far, 2, False, True, board, rng)
    assert decoy is not None and decoy != here


def test_relay_uses_ground_truth_when_visible() -> None:
    opp = _agent(Role.COP)
    perception.relay(opp, Position(3, 3), Position(2, 2), radius=2, message="vague, no coords")
    assert opp.belief == Position(3, 3)


def test_relay_falls_back_to_message_when_far() -> None:
    opp = _agent(Role.COP)
    perception.relay(opp, Position(5, 5), Position(1, 1), radius=2, message="I'm at (4,4)")
    assert opp.belief == Position(4, 4)


def test_agent_perceive_acquires_and_drops() -> None:
    agent = _agent(Role.COP)
    assert agent.perceive(Position(1, 1), Position(2, 2), vision_radius=2) is True
    assert agent.belief == Position(2, 2)
    # standing on the stale belief without seeing the target clears the lead
    agent.belief = Position(1, 1)
    assert agent.perceive(Position(1, 1), Position(5, 5), vision_radius=2) is False
    assert agent.belief is None
