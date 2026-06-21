"""Tests for the natural-language dialogue layer."""

from __future__ import annotations

from copthief.constants import Action, Role
from copthief.domain.models import Move, Observation, Position
from copthief.llm.mock import MockProvider
from copthief.orchestrator import dialogue


def _obs(role: Role) -> Observation:
    return Observation(role, Position(2, 2), 0, 25, 5)


def test_announce_includes_coordinate(provider: MockProvider) -> None:
    move = Move(Role.THIEF, Action.MOVE, 1, 0)
    text = dialogue.announce(provider, _obs(Role.THIEF), move, Position(3, 2))
    assert "(3,2)" in text
    assert "thief" in text


def test_parse_position_variants() -> None:
    assert dialogue.parse_position("I am at (4,5) now") == Position(4, 5)
    assert dialogue.parse_position("cell 2 3") == Position(2, 3)
    assert dialogue.parse_position("no coordinates here") is None


def test_round_trip_announce_then_parse(provider: MockProvider) -> None:
    move = Move(Role.COP, Action.MOVE, 0, 1)
    text = dialogue.announce(provider, _obs(Role.COP), move, Position(2, 3))
    assert dialogue.parse_position(text) == Position(2, 3)


def test_negotiate_setup(provider: MockProvider) -> None:
    text = dialogue.negotiate_setup(provider, Role.COP, [5, 5], 1)
    assert "cop" in text.lower()


def test_intent_to_move() -> None:
    move = dialogue.intent_to_move(Role.COP, Action.BLOCK)
    assert move.action is Action.BLOCK
