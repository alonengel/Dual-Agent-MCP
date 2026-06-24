"""Tests for the pure agent MCP session (LLM-free tool executor, PDF section 5.2)."""

from __future__ import annotations

from copthief.agents.session import AgentSession
from copthief.constants import Role
from copthief.shared.config import Config


def _session(role: Role) -> AgentSession:
    return AgentSession(role, Config.load())


def test_reset_places_agent_and_clears_history() -> None:
    session = _session(Role.THIEF)
    obs = session.reset(3, 4, barriers_left=5)
    assert (obs["x"], obs["y"]) == (3, 4)
    assert obs["history"] == []
    assert obs["barriers_left"] == 5


def test_move_updates_position() -> None:
    session = _session(Role.THIEF)
    session.reset(2, 2, 5)
    out = session.move(1, 0)
    assert out["legal"] is True
    assert (out["x"], out["y"]) == (3, 2)


def test_illegal_move_keeps_position() -> None:
    session = _session(Role.COP)
    session.reset(1, 1, 5)
    out = session.move(-1, 0)  # off the board
    assert out["legal"] is False
    assert (out["x"], out["y"]) == (1, 1)


def test_cop_places_barrier_decrements_quota() -> None:
    session = _session(Role.COP)
    session.reset(3, 3, 5)
    out = session.place_barrier()
    assert out["legal"] is True
    assert out["barriers_left"] == 4
    assert session.board.is_barrier(session.pos)


def test_thief_cannot_place_barrier() -> None:
    session = _session(Role.THIEF)
    session.reset(3, 3, 5)
    assert session.place_barrier()["legal"] is False


def test_note_records_opponent_message() -> None:
    session = _session(Role.COP)
    session.reset(1, 1, 5)
    session.note("I am at (4,4)")
    assert session.observe()["history"] == ["I am at (4,4)"]


def test_deliver_message_records_free_text() -> None:
    session = _session(Role.THIEF)
    session.reset(1, 1, 5)
    out = session.deliver_message("heading north, catch me if you can")
    assert out == {"ok": True, "count": 1}
    assert session.observe()["history"] == ["heading north, catch me if you can"]


def test_inbox_returns_full_stream_past_the_snapshot_cap() -> None:
    session = _session(Role.COP)
    session.reset(1, 1, 5)
    for i in range(7):
        session.deliver_message(f"m{i}")
    assert session.observe()["history"] == ["m2", "m3", "m4", "m5", "m6"]  # snapshot = last 5
    box = session.inbox()
    assert box["count"] == 7
    assert box["messages"] == [f"m{i}" for i in range(7)]  # full ordered mailbox
