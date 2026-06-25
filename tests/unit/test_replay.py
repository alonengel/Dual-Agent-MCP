"""Unit tests for deterministic audit-log replay (synthetic logs, fast)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from copthief.replay import ReplayError, replay_audit_log

_CFG = {"grid_size": [5, 5], "max_moves": 25, "max_barriers": 5,
        "origin": 1, "diagonal_moves": True}

# A clean, replayable 2-move sub-game ending in a capture at (1,1).
_CLEAN = [
    {"event": "subgame_start", "index": 1, "cop": [3, 1], "thief": [1, 1]},
    {"event": "turn", "index": 1, "move": 0, "role": "thief", "action": "move",
     "cop": [3, 1], "thief": [1, 2]},
    {"event": "turn", "index": 1, "move": 0, "role": "cop", "action": "move",
     "cop": [2, 1], "thief": [1, 2]},
    {"event": "turn", "index": 1, "move": 1, "role": "thief", "action": "move",
     "cop": [2, 1], "thief": [1, 1]},
    {"event": "turn", "index": 1, "move": 1, "role": "cop", "action": "move",
     "cop": [1, 1], "thief": [1, 1]},  # cop steps onto the thief -> capture
    {"event": "subgame_end", "index": 1, "outcome": "cop_win"},
]


def _write(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "audit.log"
    path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")
    return path


def test_clean_log_replays_to_the_recorded_outcome(tmp_path: Path) -> None:
    summaries = replay_audit_log(_write(tmp_path, _CLEAN), _CFG)
    assert summaries == [{"index": 1, "outcome": "cop_win"}]


def test_position_divergence_raises(tmp_path: Path) -> None:
    tampered = [dict(e) for e in _CLEAN]
    tampered[2] = {**tampered[2], "cop": [9, 9]}  # unreachable in one step -> illegal -> stays
    with pytest.raises(ReplayError, match="replayed"):
        replay_audit_log(_write(tmp_path, tampered), _CFG)


def test_outcome_divergence_raises(tmp_path: Path) -> None:
    tampered = [dict(e) for e in _CLEAN]
    tampered[-1] = {**tampered[-1], "outcome": "thief_win"}
    with pytest.raises(ReplayError, match="outcome"):
        replay_audit_log(_write(tmp_path, tampered), _CFG)


def test_turn_after_game_end_raises(tmp_path: Path) -> None:
    extra = {"event": "turn", "index": 1, "move": 2, "role": "thief", "action": "move",
             "cop": [1, 1], "thief": [1, 2]}
    broken = _CLEAN[:-1] + [extra, _CLEAN[-1]]  # a turn after the capturing move
    with pytest.raises(ReplayError, match="after the game ended"):
        replay_audit_log(_write(tmp_path, broken), _CFG)
