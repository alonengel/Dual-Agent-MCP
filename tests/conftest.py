"""Shared pytest fixtures."""

from __future__ import annotations

import random

import pytest

from copthief.domain.board import Board
from copthief.domain.models import Position
from copthief.llm.mock import MockProvider


@pytest.fixture
def board() -> Board:
    """A 5x5 board with origin 1 and diagonal movement enabled."""
    return Board(5, 5, origin=1, diagonal=True)


@pytest.fixture
def small_board() -> Board:
    """A 2x2 board for fast pipeline sanity checks."""
    return Board(2, 2, origin=1, diagonal=True)


@pytest.fixture
def provider() -> MockProvider:
    """Deterministic offline LLM provider."""
    return MockProvider()


@pytest.fixture
def rng() -> random.Random:
    """Seeded RNG for reproducible tests."""
    return random.Random(42)


@pytest.fixture
def game_cfg() -> dict:
    """Minimal game config for fast tests."""
    return {
        "grid_size": [3, 3],
        "max_moves": 5,
        "num_games": 2,
        "max_barriers": 5,
        "origin": 1,
        "diagonal_moves": True,
    }


@pytest.fixture
def scoring_cfg() -> dict:
    """Standard scoring config."""
    return {"cop_win": 20, "thief_win": 10, "cop_loss": 5, "thief_loss": 5}


def pos(x: int, y: int) -> Position:
    """Convenience constructor for a Position."""
    return Position(x, y)
