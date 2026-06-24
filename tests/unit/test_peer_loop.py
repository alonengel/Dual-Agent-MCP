"""Tests for the peer turn-loop + wire envelope: capture, survival, dedup, chatter-skip."""

from __future__ import annotations

import asyncio

import pytest

from copthief.constants import Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Position
from copthief.interop import commitment, wire
from copthief.interop.peer_loop import PeerDesyncError, PeerLoop
from copthief.interop.peer_match import PeerMatch
from copthief.llm.mock import MockProvider
from copthief.orchestrator.agent import Agent
from copthief.strategy.adaptive import AdaptiveStrategy


def _board() -> Board:
    return Board(5, 5, origin=1)


def _agent(role: Role) -> Agent:
    return Agent(role, AdaptiveStrategy(), MockProvider())


def _const(text: str):
    async def recv() -> str:
        return text
    return recv


def test_wire_encode_decode_roundtrip() -> None:
    msg = wire.encode("heading north", (2, 3), "a" * 64, "ff01beef", "b" * 64)
    env = wire.decode("noise " + msg + " more noise")
    assert env == {"cell": (2, 3), "commit": "a" * 64, "nonce": "ff01beef", "state": "b" * 64}


def test_wire_encode_flattens_multiline_prose() -> None:
    # A multi-line / pipe-laden taunt must not push the block off line 1 (peers may parse only
    # the first line), so encode flattens whitespace and neutralises the field-separator '|'.
    msg = wire.encode("Catch me\nif you can | now", (0, 5), "c" * 64, "deadbeef", "d" * 64)
    assert "\n" not in msg and msg.count("|") == 5  # '||' + 3 field seps; prose '|' neutralised
    assert wire.decode(msg.splitlines()[0]) == {
        "cell": (0, 5), "commit": "c" * 64, "nonce": "deadbeef", "state": "d" * 64}


def test_wire_decode_returns_none_without_block() -> None:
    assert wire.decode("just prose, no verifiable block here") is None


def test_peer_match_cop_capture_confirmed_by_commit_reveal() -> None:
    match = PeerMatch(_board(), _agent(Role.COP), _agent(Role.THIEF), 25, 5, radius=5)
    outcome, rounds = match.play(Position(2, 3), Position(3, 3))
    assert outcome is Outcome.COP_WIN and 1 <= rounds <= 25


def test_peer_match_thief_survives_tiny_budget() -> None:
    match = PeerMatch(_board(), _agent(Role.COP), _agent(Role.THIEF), 1, 5, radius=1)
    outcome, rounds = match.play(Position(1, 1), Position(5, 5))
    assert outcome is Outcome.THIEF_WIN and rounds == 1


async def test_peer_loop_full_disclosure_capture_is_deterministic() -> None:
    cop = PeerLoop(Role.COP, _agent(Role.COP), Board(5, 5, origin=1), 25)
    thief = PeerLoop(Role.THIEF, _agent(Role.THIEF), Board(5, 5, origin=1), 25)
    cop_inbox: asyncio.Queue = asyncio.Queue()
    thief_inbox: asyncio.Queue = asyncio.Queue()
    (oc, rc), (ot, rt) = await asyncio.gather(
        cop.play(Position(2, 3), thief_inbox.put, cop_inbox.get),
        thief.play(Position(3, 3), cop_inbox.put, thief_inbox.get))
    assert oc is Outcome.COP_WIN and ot is Outcome.COP_WIN and rc == rt


async def test_peer_loop_thief_survives_when_budget_exhausted() -> None:
    cop = PeerLoop(Role.COP, _agent(Role.COP), Board(5, 5, origin=1), 1)
    thief = PeerLoop(Role.THIEF, _agent(Role.THIEF), Board(5, 5, origin=1), 1)
    cop_inbox: asyncio.Queue = asyncio.Queue()
    thief_inbox: asyncio.Queue = asyncio.Queue()
    (oc, _), (ot, _) = await asyncio.gather(
        cop.play(Position(1, 1), thief_inbox.put, cop_inbox.get),
        thief.play(Position(5, 5), cop_inbox.put, thief_inbox.get))
    assert oc is Outcome.THIEF_WIN and ot is Outcome.THIEF_WIN


async def test_peer_loop_rejects_commit_that_does_not_open() -> None:
    loop = PeerLoop(Role.COP, _agent(Role.COP), _board(), 25)
    loop.pos = Position(2, 3)
    bad = wire.encode("over here", (0, 0), "a" * 64, "ff", "b" * 64)  # commit != cell+nonce
    with pytest.raises(PeerDesyncError):
        await loop._recv_ply(1, _const(bad))


async def test_peer_loop_tolerates_state_hash_mismatch() -> None:
    board = _board()
    loop = PeerLoop(Role.COP, _agent(Role.COP), board, 25)
    pos, nonce = Position(3, 3), commitment.new_nonce()
    msg = wire.encode("here", commitment.to_cell(pos, board),
                      commitment.commit(pos, board, nonce), nonce, "b" * 64)  # bad STATE
    await loop._recv_ply(1, _const(msg))  # non-fatal (barriers off): does not raise
    assert loop.opp == pos  # still adopts the commit-verified move block


async def test_peer_loop_skips_non_block_chatter() -> None:
    board = _board()
    loop = PeerLoop(Role.COP, _agent(Role.COP), board, 25)
    pos, nonce = Position(3, 3), commitment.new_nonce()
    block = wire.encode("here", commitment.to_cell(pos, board),
                        commitment.commit(pos, board, nonce), nonce, loop._state(1, False))
    queue = ["Handshake: I'm the THIEF, no move in this one", block]

    async def recv() -> str:
        return queue.pop(0)

    await loop._recv_ply(1, recv)
    assert loop.opp == pos and queue == []  # greeting skipped, move block applied


async def test_peer_loop_skips_duplicate_commit_block() -> None:
    board = _board()
    loop = PeerLoop(Role.COP, _agent(Role.COP), board, 25)
    state = loop._state(1, False)
    dup_pos, dup_nonce = Position(3, 3), commitment.new_nonce()
    dup_commit = commitment.commit(dup_pos, board, dup_nonce)
    loop._seen.add(dup_commit)  # we already applied this block once
    dup = wire.encode("again", commitment.to_cell(dup_pos, board), dup_commit, dup_nonce, state)
    fresh_pos, fresh_nonce = Position(2, 2), commitment.new_nonce()
    fresh = wire.encode("fresh", commitment.to_cell(fresh_pos, board),
                        commitment.commit(fresh_pos, board, fresh_nonce), fresh_nonce, state)
    queue = [dup, fresh]

    async def recv() -> str:
        return queue.pop(0)

    await loop._recv_ply(1, recv)
    assert loop.opp == fresh_pos and queue == []  # duplicate skipped, fresh block applied
