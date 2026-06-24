"""Tests for the Agent wrapper (belief tracking and decisions)."""

from __future__ import annotations

from copthief.constants import Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.llm.base import LLMProvider
from copthief.llm.mock import MockProvider
from copthief.orchestrator.agent import Agent
from copthief.strategy.heuristic import HeuristicStrategy


def _agent(role: Role) -> Agent:
    return Agent(role, HeuristicStrategy(), MockProvider())


class _CellProvider(LLMProvider):
    """A provider whose reply names a specific cell — emulates an LLM choosing its move."""

    def __init__(self, cell: tuple[int, int]):
        super().__init__("cell", 0.0, 16)
        self._cell = cell

    def _complete(self, system: str, user: str) -> str:
        return f"I slip to ({self._cell[0]},{self._cell[1]})."


def test_decide_is_llm_driven_when_proposal_is_legal(board: Board) -> None:
    cop = Agent(Role.COP, HeuristicStrategy(), _CellProvider((2, 1)))  # a legal neighbour of (1,1)
    cop.belief = Position(5, 5)
    move = cop.decide(Observation(Role.COP, Position(1, 1), 0, 25, 5), board)
    assert cop.last_source == "llm" and (move.dx, move.dy) == (1, 0)  # the LLM's pick (2,1)


def test_decide_falls_back_to_strategy_without_legal_proposal(board: Board) -> None:
    cop = _agent(Role.COP)  # MockProvider gives no coordinate -> strategy decides
    cop.belief = Position(5, 5)
    move = cop.decide(Observation(Role.COP, Position(1, 1), 0, 25, 5), board)
    assert cop.last_source == "fallback" and (move.dx, move.dy) == (1, 1)  # strategy toward (5,5)


def test_decide_uses_strategy_when_llm_moves_disabled(board: Board) -> None:
    # Even though the provider would propose a (legal) cell, llm_moves=False bypasses the LLM
    # entirely so the strategy decides the move (the inter-group competitive configuration).
    cop = Agent(Role.COP, HeuristicStrategy(), _CellProvider((2, 1)), llm_moves=False)
    cop.belief = Position(5, 5)
    move = cop.decide(Observation(Role.COP, Position(1, 1), 0, 25, 5), board)
    assert cop.last_source == "strategy" and (move.dx, move.dy) == (1, 1)  # strategy toward (5,5)


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
