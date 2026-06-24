"""Drive the 6-sub-game inter-group bonus series and assemble the §12.2 match dict.

Per PDF §12.1 the role swaps mid-series: Group A (`group_1`) is cop in sub-games 0–2, Group B
(`group_2`) cop in 3–5. We are `group_2` (anrbj666) with `group_1` = ImreEyal, so ``OUR_SCHEDULE``
is **thief-first**. Each sub-game is played by a :class:`PeerLoop` over the async mailbox transport
— the per-sub-game I/O is *injected*, so this orchestration is unit-tested in-process (two series
wired over queues) and the live wiring lives in :func:`transport.live_io`. Results are scored into
the byte-canonical match dict (0-based ``sub_games`` + per-group ``totals_by_group``) that
:func:`reporting.report.build_bonus_report` serialises. Start cells are the agreed canonical
``[0,0]`` (cop) / ``[4,4]`` (thief), mapped into our own frame.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from copthief.constants import Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Position
from copthief.domain.scoring import ScoreBook
from copthief.interop import peer
from copthief.interop.peer_loop import PeerLoop, Recv, Send
from copthief.orchestrator.agent import Agent

# We are group_2 (anrbj666); per §12.1 group_1 (ImreEyal) is cop first, so we are thief first.
OUR_SCHEDULE: list[Role] = [Role.THIEF, Role.THIEF, Role.THIEF, Role.COP, Role.COP, Role.COP]

IOFor = Callable[[int, Role], tuple[Send, Recv]]
AgentFor = Callable[[Role], Agent]
BoardFor = Callable[[], Board]
StartsFor = Callable[[int], dict[Role, Position]]


def our_starts(board: Board) -> dict[Role, Position]:
    """Fixed canonical starts mapped into our frame: cop top-left ``[0,0]``, thief bottom-right
    ``[H-1, W-1]`` (e.g. [0,0]/[4,4] on 5x5, [0,0]/[7,7] on 8x8)."""
    return {Role.COP: peer.from_cell((0, 0), board),
            Role.THIEF: peer.from_cell((board.height - 1, board.width - 1), board)}


def derive_starts(seed: str, index: int, board: Board) -> dict[Role, Position]:
    """Deterministic per-sub-game starts both engines compute identically (no RNG divergence).

    ``cop``/``thief`` cell indices come from ``SHA-256(f"{seed}:{index}")`` mod N² (N = columns),
    nudged apart if equal, then mapped from the canonical 0-based ``[row,col]`` frame into ours.
    Both teams must use the same ``seed`` + this exact algorithm (diff a test vector first)."""
    n = board.width * board.height
    digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
    cop_idx = digest[0] % n
    thief_idx = digest[1] % n
    if thief_idx == cop_idx:
        thief_idx = (thief_idx + 1) % n
    cop = (cop_idx // board.width, cop_idx % board.width)
    thief = (thief_idx // board.width, thief_idx % board.width)
    return {Role.COP: peer.from_cell(cop, board), Role.THIEF: peer.from_cell(thief, board)}


async def play_series(schedule: list[Role], agent_for: AgentFor, io_for: IOFor,
                      board_for: BoardFor, starts_for: StartsFor,
                      max_moves: int) -> list[tuple[Role, Outcome, int]]:
    """Play each sub-game in order; return ``(role_we_played, outcome, rounds)`` per sub-game.

    ``starts_for(index)`` gives the start cells for that sub-game (fixed or seed-derived)."""
    results: list[tuple[Role, Outcome, int]] = []
    for index, role in enumerate(schedule):
        loop = PeerLoop(role, agent_for(role), board_for(), max_moves)
        send, recv = io_for(index, role)
        outcome, rounds = await loop.play(starts_for(index)[role], send, recv)
        results.append((role, outcome, rounds))
    return results


def score_series(results: list[tuple[Role, Outcome, int]], scoring: dict[str, int],
                 our_group: str, opp_group: str) -> dict:
    """Score the sub-games into the byte-canonical match dict (0-based + per-group totals)."""
    book = ScoreBook(scoring)
    sub_games: list[dict] = []
    totals = {our_group: 0, opp_group: 0}
    for index, (role, outcome, rounds) in enumerate(results):
        r = book.score_subgame(index, outcome, rounds)
        sub_games.append({"index": index, "outcome": outcome.value,
                          "cop_score": r.cop_score, "thief_score": r.thief_score})
        ours, theirs = ((r.cop_score, r.thief_score) if role is Role.COP
                        else (r.thief_score, r.cop_score))
        totals[our_group] += ours
        totals[opp_group] += theirs
    return {"sub_games": sub_games, "totals_by_group": totals}
