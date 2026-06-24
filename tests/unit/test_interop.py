"""Tests for inter-group crypto primitives: commit-reveal, common-state hash, canonical reports."""

from __future__ import annotations

from copthief.domain.board import Board
from copthief.domain.models import Position
from copthief.interop import canonical, commitment, peer
from copthief.reporting.report import build_bonus_report

# Agreed test vectors from the partner team (group ImreEyal) — interop must match exactly.
PARTNER_COMMIT = "3b37bed7b664a8aa96e14072f885fee2cb617bfb57cd42c1fa7430c8d98f2d22"
PARTNER_STATE = "137b977dba629e0bfbc1b49b52f899f18d71c07adbef2f11ecb1d84704880385"


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


def test_commit_matches_partner_test_vector() -> None:
    board = _board()
    pos = peer.from_cell((2, 3), board)  # the cell their commit vector binds (row=2, col=3)
    assert commitment.commit(pos, board, "abc123") == PARTNER_COMMIT


def test_state_hash_matches_partner_test_vector() -> None:
    assert commitment.state_hash({(1, 1)}, "cop", 4) == PARTNER_STATE


def test_canonical_report_digest_matches_and_differs() -> None:
    r1 = {"report_type": "bonus_game", "groups": {"group_1": "A", "group_2": "B"}}
    r2 = {"report_type": "bonus_game", "groups": {"group_1": "A", "group_2": "B"}}
    assert canonical.reports_agree(r1, r2)
    r3 = {"report_type": "bonus_game", "groups": {"group_1": "A", "group_2": "C"}}
    assert not canonical.reports_agree(r1, r3)


def test_bonus_report_uses_winner_subgame_schema() -> None:
    g = {"group_name": "A", "students": [], "github_repo": "", "cop_url": "", "thief_url": ""}
    match = {"totals_by_group": {"A": 20, "B": 10},
             "sub_games": [{"index": 1, "outcome": "cop_win", "moves_played": 7,
                            "cop_score": 20, "thief_score": 5}]}
    rep = build_bonus_report(g, {**g, "group_name": "B"}, match)
    assert rep["sub_games"] == [{"index": 1, "winner": "cop", "cop_score": 20, "thief_score": 5}]


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
