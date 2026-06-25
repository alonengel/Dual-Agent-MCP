"""Deterministic replay of a recorded game from its audit log (reproducibility guard).

Re-applies every logged turn to a fresh engine (the real rules + subgame state machine) and
checks each reconstructed position — and each sub-game's final outcome — matches what was
recorded. Any divergence raises :class:`ReplayError` (fail loud). This proves a saved game
is reproducible from its log alone and guards against silent engine regressions.

Works against this project's JSON-lines audit log (each turn records the post-move
``cop``/``thief`` cells and the action).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from copthief.constants import Action, Role
from copthief.domain.board import Board
from copthief.domain.models import Move, Position
from copthief.domain.subgame import Subgame


class ReplayError(AssertionError):
    """A recorded game diverged from a deterministic replay — fail loud."""


def _board(cfg: dict[str, Any]) -> Board:
    """Build the board from the game config section."""
    width, height = cfg.get("grid_size", [5, 5])
    return Board(int(width), int(height), int(cfg.get("origin", 1)),
                 bool(cfg.get("diagonal_moves", True)))


def _reconstruct(game: Subgame, entry: dict[str, Any]) -> Move:
    """Rebuild the move that produced this logged turn from the recorded positions."""
    role = Role(entry["role"])
    prev = game.position_of(role)
    new = Position(*(entry["cop"] if role is Role.COP else entry["thief"]))
    if entry["action"] == Action.BLOCK.value:
        return Move(role, Action.BLOCK)
    if new == prev:  # unchanged cell => a STAY (or a rejected move that kept position)
        return Move(role, Action.STAY)
    return Move(role, Action.MOVE, new.x - prev.x, new.y - prev.y)


def _replay_turn(game: Subgame, entry: dict[str, Any], index: int) -> None:
    """Apply one reconstructed turn and assert the resulting cell matches the log."""
    if game.finished():
        raise ReplayError(f"sub-game {index}: a turn was logged after the game ended")
    role = Role(entry["role"])
    game.apply(_reconstruct(game, entry))
    actual = game.position_of(role).as_tuple()
    expected = tuple(entry["cop"] if role is Role.COP else entry["thief"])
    if actual != expected:
        raise ReplayError(f"sub-game {index} move {entry['move']} {role.value}: "
                          f"replayed {actual} != recorded {expected}")


def replay_audit_log(audit_path: Path, game_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Replay every sub-game in the log; return per-sub-game summaries or raise ReplayError."""
    entries = [json.loads(x) for x in audit_path.read_text(encoding="utf-8").splitlines()]
    summaries: list[dict[str, Any]] = []
    game: Subgame | None = None
    index = 0
    for entry in entries:
        event = entry.get("event")
        if event == "subgame_start":
            index = entry["index"]
            game = Subgame(_board(game_cfg), Position(*entry["cop"]), Position(*entry["thief"]),
                           int(game_cfg.get("max_moves", 25)), int(game_cfg.get("max_barriers", 5)))
        elif event == "turn" and game is not None:
            _replay_turn(game, entry, index)
        elif event == "subgame_end" and game is not None:
            outcome = game.outcome.value if game.outcome else "technical_loss"
            if outcome != entry["outcome"]:
                raise ReplayError(f"sub-game {index}: replayed outcome {outcome!r} "
                                  f"!= recorded {entry['outcome']!r}")
            summaries.append({"index": index, "outcome": outcome})
            game = None
    return summaries
