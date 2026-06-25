"""Tests for the animated board playback (frame extraction + headless GIF export)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)  # headless: never try to open a window in tests

from copthief.gui.animate import _frames, animate_audit, build_animation  # noqa: E402

# A two-subgame audit log: subgame 1 has a barrier drop; subgame 2 must reset it.
_TURNS = [
    {"event": "negotiation", "role": "cop"},  # ignored by the frame extractor
    {"event": "turn", "index": 1, "move": 0, "role": "thief", "action": "move",
     "cop": [3, 3], "thief": [1, 1]},
    {"event": "turn", "index": 1, "move": 1, "role": "cop", "action": "block",
     "cop": [3, 3], "thief": [1, 1]},
    {"event": "turn", "index": 1, "move": 1, "role": "thief", "action": "move",
     "cop": [3, 3], "thief": [1, 2]},
    {"event": "turn", "index": 2, "move": 0, "role": "thief", "action": "move",
     "cop": [5, 5], "thief": [2, 2]},
]


def _write_audit(tmp_path: Path) -> Path:
    """Materialize the synthetic audit log as JSON-lines."""
    path = tmp_path / "game_audit.log"
    path.write_text("\n".join(json.dumps(t) for t in _TURNS), encoding="utf-8")
    return path


def test_frames_skip_non_turns_and_track_barriers(tmp_path: Path) -> None:
    frames = _frames(_write_audit(tmp_path))
    assert len(frames) == 4  # the negotiation entry is excluded
    # The block at move 1 is visible from that frame onward within subgame 1...
    assert frames[1]["barriers"] == {(3, 3)}
    assert frames[2]["barriers"] == {(3, 3)}
    # ...but subgame 2 starts with a clean board.
    assert frames[3]["index"] == 2
    assert frames[3]["barriers"] == set()


def test_frames_missing_file_is_empty(tmp_path: Path) -> None:
    assert _frames(tmp_path / "does_not_exist.log") == []


def test_build_animation_none_without_frames(tmp_path: Path) -> None:
    empty = tmp_path / "empty.log"
    empty.write_text("", encoding="utf-8")
    assert build_animation(empty) is None


def test_animate_audit_writes_gif(tmp_path: Path) -> None:
    audit = _write_audit(tmp_path)
    gif = animate_audit(audit, tmp_path, save_gif=True, show=False, interval=200)
    assert gif is not None
    assert gif == tmp_path / "assets" / "demo_animation.gif"
    assert gif.exists() and gif.stat().st_size > 0
