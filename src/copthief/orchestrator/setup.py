"""Match setup: build a board and randomized starting positions from config."""

from __future__ import annotations

import random
from typing import Any

from copthief.constants import Role
from copthief.domain.board import Board
from copthief.domain.models import Observation
from copthief.domain.subgame import Subgame


def build_subgame(game_cfg: dict[str, Any], rng: random.Random) -> Subgame:
    """Create a fresh subgame with distinct random cop/thief start cells."""
    width, height = game_cfg.get("grid_size", [5, 5])
    origin = int(game_cfg.get("origin", 1))
    diagonal = bool(game_cfg.get("diagonal_moves", True))
    board = Board(width, height, origin, diagonal)

    thief = board.random_free_cell(rng, exclude=set())
    cop = board.random_free_cell(rng, exclude={thief.as_tuple()})
    return Subgame(
        board=board,
        cop=cop,
        thief=thief,
        max_moves=int(game_cfg.get("max_moves", 25)),
        max_barriers=int(game_cfg.get("max_barriers", 5)),
    )


def observe(game: Subgame, role: Role, last_message: str = "") -> Observation:
    """Build the partial observation handed to the agent of ``role``."""
    return Observation(
        role=role,
        self_pos=game.position_of(role),
        move_number=game.move_number,
        max_moves=game.max_moves,
        barriers_left=game.barriers_left,
        last_opponent_message=last_message,
    )
