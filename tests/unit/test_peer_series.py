"""Tests for the sub-game series driver + SG-framed live transport routing."""

from __future__ import annotations

import asyncio

from copthief.constants import Outcome, Role
from copthief.domain.board import Board
from copthief.interop import commitment, peer_series
from copthief.interop.peer_loop import PeerLoop
from copthief.llm.mock import MockProvider
from copthief.orchestrator.agent import Agent
from copthief.strategy.adaptive import AdaptiveStrategy

SCORING = {"cop_win": 20, "thief_win": 10, "cop_loss": 5, "thief_loss": 5}


def _agent(role: Role) -> Agent:
    return Agent(role, AdaptiveStrategy(), MockProvider())


def test_derive_starts_deterministic_distinct_in_bounds() -> None:
    board = Board(8, 8, origin=1)
    a = peer_series.derive_starts("seed-xyz", 0, board)
    assert a == peer_series.derive_starts("seed-xyz", 0, board)  # deterministic
    assert a[Role.COP] != a[Role.THIEF]                          # distinct
    assert a != peer_series.derive_starts("seed-xyz", 1, board)  # varies by index
    for role in (Role.COP, Role.THIEF):
        r, c = commitment.to_cell(a[role], board)
        assert 0 <= r < 8 and 0 <= c < 8                         # in bounds


def test_our_starts_scale_to_board_size() -> None:
    b5, b8 = Board(5, 5, origin=1), Board(8, 8, origin=1)
    s5, s8 = peer_series.our_starts(b5), peer_series.our_starts(b8)
    assert commitment.to_cell(s5[Role.COP], b5) == (0, 0)
    assert commitment.to_cell(s5[Role.THIEF], b5) == (4, 4)
    assert commitment.to_cell(s8[Role.COP], b8) == (0, 0)
    assert commitment.to_cell(s8[Role.THIEF], b8) == (7, 7)


def test_score_series_builds_zero_based_subgames_and_per_group_totals() -> None:
    results = [(Role.THIEF, Outcome.COP_WIN, 5), (Role.COP, Outcome.THIEF_WIN, 25)]
    match = peer_series.score_series(results, SCORING, "anrbj666", "ImreEyal")
    assert [s["index"] for s in match["sub_games"]] == [0, 1]
    assert match["sub_games"][0] == {"index": 0, "outcome": "cop_win",
                                     "cop_score": 20, "thief_score": 5}
    # SG0 cop_win, we were thief -> +5 us / +20 them; SG1 thief_win, we were cop -> +5 us / +10 them
    assert match["totals_by_group"] == {"anrbj666": 10, "ImreEyal": 30}


async def test_play_series_runs_full_role_swap_series_and_scores() -> None:
    def board_for() -> Board:
        return Board(5, 5, origin=1)

    starts = peer_series.our_starts(board_for())
    tasks: list = []

    def io_for(index: int, role: Role):
        our_in: asyncio.Queue = asyncio.Queue()
        opp_in: asyncio.Queue = asyncio.Queue()
        opp_role = Role.COP if role is Role.THIEF else Role.THIEF
        opp = PeerLoop(opp_role, _agent(opp_role), board_for(), 25)
        tasks.append(asyncio.create_task(opp.play(starts[opp_role], our_in.put, opp_in.get)))
        return opp_in.put, our_in.get

    results = await peer_series.play_series(
        peer_series.OUR_SCHEDULE, _agent, io_for, board_for, lambda i: starts, 25)
    await asyncio.gather(*tasks)
    match = peer_series.score_series(results, SCORING, "anrbj666", "ImreEyal")
    assert [s["index"] for s in match["sub_games"]] == [0, 1, 2, 3, 4, 5]
    points = sum(s["cop_score"] + s["thief_score"] for s in match["sub_games"])
    assert sum(match["totals_by_group"].values()) == points


async def test_live_io_sg_framing_holds_skips_and_applies(monkeypatch) -> None:
    from copthief.interop import transport
    inbox = ["SG:0 m0", "no-frame raw", "SG:2 m2", "SG:0 stale", "SG:1 m1"]  # arrival order
    sent: list[str] = []

    async def fake_read(url: str, token: str) -> list[str]:
        return list(inbox)

    async def fake_deliver(url: str, token: str, text: str, retries: int = 5) -> None:
        sent.append(text)

    monkeypatch.setattr(transport, "read_inbox", fake_read)
    monkeypatch.setattr(transport, "deliver", fake_deliver)
    io = transport.live_io({"thief": "u", "cop": "u"}, {"thief": "o", "cop": "o"},
                           "tok", {"thief": "k", "cop": "k"}, poll_interval=0.0)

    s0, r0 = io(0, Role.THIEF)
    assert await r0() == "m0"                 # current sub-game -> applied (SG stripped)
    assert await r0() == "no-frame raw"       # untagged -> tolerated/applied
    await s0("hi || BLOCK")
    assert sent == ["SG:0 hi || BLOCK"]       # send stamps our sub-game index

    _, r1 = io(1, Role.THIEF)
    assert await r1() == "m1"                 # SG:2 held, SG:0 stale skipped, SG:1 applied

    _, r2 = io(2, Role.THIEF)
    assert await r2() == "m2"                 # the held later-sub-game message surfaces here
