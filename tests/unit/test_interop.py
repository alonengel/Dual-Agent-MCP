"""Tests for the inter-group peer-interop layer: commit-reveal, canonical reports, envelopes."""

from __future__ import annotations

from copthief.constants import Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Position
from copthief.interop import canonical, commitment, peer
from copthief.interop.peer_match import PeerMatch
from copthief.llm.mock import MockProvider
from copthief.orchestrator.agent import Agent
from copthief.strategy.adaptive import AdaptiveStrategy


def _board() -> Board:
    return Board(5, 5, origin=1)


def test_to_cell_and_inverse_roundtrip() -> None:
    board = _board()
    for pos in (Position(1, 1), Position(5, 5), Position(3, 4)):
        assert peer.from_cell(commitment.to_cell(pos, board), board) == pos


def test_commit_verifies_and_rejects_wrong_cell_or_nonce() -> None:
    board = _board()
    nonce = commitment.new_nonce()
    c = commitment.commit(Position(2, 3), board, nonce)
    assert commitment.verify(c, Position(2, 3), board, nonce)
    assert not commitment.verify(c, Position(2, 4), board, nonce)        # wrong cell
    assert not commitment.verify(c, Position(2, 3), board, "deadbeef")   # wrong nonce


def test_state_hash_detects_any_change() -> None:
    base = commitment.state_hash({(0, 0)}, "cop", 3)
    assert base == commitment.state_hash({(0, 0)}, "cop", 3)      # deterministic
    assert base != commitment.state_hash({(0, 0)}, "thief", 3)    # turn changed
    assert base != commitment.state_hash({(0, 0)}, "cop", 4)      # move_count changed
    assert base != commitment.state_hash(set(), "cop", 3)         # barriers changed


def test_canonical_report_digest_matches_and_differs() -> None:
    r1 = {"report_type": "bonus_game", "groups": {"group_1": "A", "group_2": "B"}}
    r2 = {"report_type": "bonus_game", "groups": {"group_1": "A", "group_2": "B"}}
    assert canonical.reports_agree(r1, r2)
    r3 = {"report_type": "bonus_game", "groups": {"group_1": "A", "group_2": "C"}}
    assert not canonical.reports_agree(r1, r3)


def test_envelope_state_sync_and_capture_confirmation() -> None:
    board = _board()
    nonce = commitment.new_nonce()
    thief = Position(3, 3)
    env = peer.make_envelope("slipping away", thief, board, nonce, [(0, 0)], "thief", 2,
                             reveal=True)
    assert peer.state_in_sync(env, [(0, 0)], "thief", 2)
    assert not peer.state_in_sync(env, [(0, 0)], "cop", 2)             # desync
    assert peer.confirm_capture(env["commit"], env["reveal"], board, claim_cell=thief)
    assert not peer.confirm_capture(env["commit"], env["reveal"], board, Position(1, 1))


def test_confirm_capture_rejects_tampered_reveal_and_missing_reveal() -> None:
    board = _board()
    nonce = commitment.new_nonce()
    env = peer.make_envelope("here", Position(4, 4), board, nonce, [], "thief", 1, reveal=True)
    env["reveal"]["nonce"] = "tampered"
    assert not peer.confirm_capture(env["commit"], env["reveal"], board, Position(4, 4))
    assert not peer.confirm_capture(env["commit"], None, board, Position(4, 4))


def _agent(role: Role) -> Agent:
    return Agent(role, AdaptiveStrategy(), MockProvider())


def test_peer_match_cop_capture_confirmed_by_commit_reveal() -> None:
    match = PeerMatch(_board(), _agent(Role.COP), _agent(Role.THIEF), 25, 5, radius=5)
    outcome, rounds = match.play(Position(2, 3), Position(3, 3))
    assert outcome is Outcome.COP_WIN and 1 <= rounds <= 25


def test_peer_match_thief_survives_tiny_budget() -> None:
    match = PeerMatch(_board(), _agent(Role.COP), _agent(Role.THIEF), 1, 5, radius=1)
    outcome, rounds = match.play(Position(1, 1), Position(5, 5))
    assert outcome is Outcome.THIEF_WIN and rounds == 1
