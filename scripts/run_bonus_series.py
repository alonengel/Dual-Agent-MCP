"""Run the LIVE 6-sub-game inter-group bonus series against the partner's MCP mailboxes.

Wires the async peer turn-loop (`interop.peer_series` + `transport.live_io`) with our **real
Claude agents** (CLI-first, Anthropic-API fallback — never mock; provider comes from
`COPTHIEF_LLM_PROVIDER=claude` in `.env`). Plays the agreed role-swap series (we are group_2 =
anrbj666: thief in 0-2, cop in 3-5), scores it into the byte-canonical `bonus_game` report,
saves it, and prints our SHA-256 for the two-phase confirm. Emailing is a deliberate, separate
step: only send once the partner's digest matches ours (PDF §12.2 → else 0/0).

Usage: ``run_bonus_series.py --opp-cop <url> --opp-thief <url>``. We read our own inbox on
localhost:8080 (fast); the partner reaches us via the public tunnel. Tokens: ours =
COPTHIEF_MCP_TOKEN, theirs = OPPONENT_COP_TOKEN (one token for both their URLs).
"""

from __future__ import annotations

import argparse
import asyncio
import os

from copthief.domain.board import Board
from copthief.interop import peer_series, transport
from copthief.interop.canonical import digest
from copthief.llm.factory import build_llm_clients, build_provider
from copthief.orchestrator.agent import Agent
from copthief.reporting.emailer import send_report_email
from copthief.reporting.report import build_bonus_report, save_report
from copthief.shared.config import Config
from copthief.strategy.factory import build_strategy

OPP_GROUP = {
    "group_name": "ImreEyal",
    "students": ["Imree Cohen", "Eyal Shtinmetz"],
    "github_repo": "https://github.com/Imreec/mcp-cop-thief",
}


def _board(config: Config, size: int) -> Board:
    g = config.section("game")
    return Board(size, size, int(g.get("origin", 1)), bool(g.get("diagonal_moves", True)))


async def _confirm_and_email(report: dict, sha: str, ours: dict, opp: dict, our_token: str,
                             opp_token: str, email_to: str, gate, send: bool) -> None:
    """Automated two-phase confirm: swap report hashes over the channel; email iff they match
    (and only when ``send`` is set — a deliberate press, matching the partner's send policy)."""
    peer_sha = await transport.exchange_hash(sha, opp["cop"], opp_token, ours["cop"], our_token)
    if peer_sha is None:
        print("[series] no peer hash within timeout -> NOT emailing; confirm + send manually",
              flush=True)
    elif peer_sha != sha:
        print(f"[series] HASH MISMATCH peer={peer_sha[:12]}... ours={sha[:12]}... -> NOT emailing "
              "(§12.2: a mismatch is 0/0, so we abort instead of sending)", flush=True)
    elif not send:
        print(f"[series] HASHES MATCH ({sha[:12]}...) -> re-run with --send to email, or send "
              "the saved report manually", flush=True)
    else:
        print(f"[series] HASHES MATCH ({sha[:12]}...) -> emailing report to {email_to}", flush=True)
        ok = send_report_email(email_to, "CopThief inter-group bonus game report "
                               "(anrbj666 vs ImreEyal)", report, gate=gate)
        print(f"[series] email {'sent' if ok else 'FAILED (check Gmail setup)'}", flush=True)


async def _run(opp_cop: str, opp_thief: str, grid_size: int, rounds: int, send: bool,
               email_to: str, seed: str) -> None:
    config = Config.load()
    provider_name = os.environ.get("COPTHIEF_LLM_PROVIDER", config.get("llm.provider", "mock"))
    if provider_name.lower() == "mock":
        raise SystemExit("Refusing to run the live bonus series with the mock provider. "
                         "Set COPTHIEF_LLM_PROVIDER=claude in .env.")
    gate, meter = build_llm_clients(config)

    def agent_for(role):
        # Competitive run: the strategy decides moves (stronger, faster, never self-captures);
        # the LLM still voices every turn in free text (PDF §5.1 communication requirement).
        return Agent(role, build_strategy(config.section("strategy")),
                     build_provider(config.section("llm"), gate, meter), llm_moves=False)

    mcp = config.section("mcp")
    ours = {"cop": os.environ.get("COPTHIEF_COP_URL", "http://127.0.0.1:8080/cop/mcp"),
            "thief": os.environ.get("COPTHIEF_THIEF_URL", "http://127.0.0.1:8080/thief/mcp")}
    opp = {"cop": opp_cop, "thief": opp_thief}
    our_token = os.environ["COPTHIEF_MCP_TOKEN"]
    opp_token = os.environ["OPPONENT_COP_TOKEN"]
    base_io = transport.live_io(ours, opp, our_token, {"cop": opp_token, "thief": opp_token})

    def io_for(index, role):
        send, recv = base_io(index, role)

        async def lsend(text: str) -> None:
            print(f"[ply] sg{index} {role.value} SEND -> {text[:70]}", flush=True)
            await send(text)

        async def lrecv() -> str:
            msg = await recv()
            print(f"[ply] sg{index} {role.value} RECV <- {msg[:70]}", flush=True)
            return msg

        return lsend, lrecv

    board0 = _board(config, grid_size)
    fixed = None if seed else peer_series.our_starts(board0)

    def starts_for(i: int) -> dict:
        return peer_series.derive_starts(seed, i, board0) if seed else fixed

    schedule_repr = [r.value for r in peer_series.OUR_SCHEDULE]
    print(f"[series] provider={provider_name} board={grid_size}x{grid_size} rounds={rounds} "
          f"seed={seed or '(fixed)'} schedule={schedule_repr}", flush=True)
    results = await peer_series.play_series(peer_series.OUR_SCHEDULE, agent_for, io_for,
                                            lambda: _board(config, grid_size), starts_for, rounds)
    for i, (role, outcome, rounds) in enumerate(results):
        print(f"[series] sub-game {i}: we={role.value} -> {outcome.value} ({rounds} rounds)",
              flush=True)

    match = peer_series.score_series(results, config.section("scoring"), "anrbj666", "ImreEyal")
    us = {"group_name": config.get("team.group_name", "anrbj666"),
          "students": config.section("team").get("students", []),
          "github_repo": config.get("team.github_repo", ""),
          "cop_url": mcp.get("cop_url"), "thief_url": mcp.get("thief_url")}
    them = {**OPP_GROUP, "cop_url": opp_cop, "thief_url": opp_thief}
    report = build_bonus_report(them, us, match, agreement=True, bonus=config.section("bonus"))
    path = save_report(report, config.root / config.get("reporting.results_dir", "results"),
                       prefix="bonus_game")
    sha = digest(report)
    print(f"\n[series] totals_by_group={match['totals_by_group']}", flush=True)
    print(f"[series] report saved: {path}", flush=True)
    print(f"[series] OUR REPORT SHA-256: {sha}", flush=True)
    recipient = email_to or config.get("reporting.email_to", "")
    await _confirm_and_email(report, sha, ours, opp, our_token, opp_token, recipient, gate, send)


def main() -> None:
    p = argparse.ArgumentParser(description="Run the live inter-group bonus series")
    p.add_argument("--opp-cop", required=True, help="partner's cop mailbox URL")
    p.add_argument("--opp-thief", required=True, help="partner's thief mailbox URL")
    p.add_argument("--grid-size", type=int, default=8, help="board size NxN (frozen bonus: 8)")
    p.add_argument("--rounds", type=int, default=12, help="max rounds/sub-game (frozen bonus: 12)")
    p.add_argument("--send", action="store_true", help="email the report on a confirmed hash match")
    p.add_argument("--email-to", default="", help="report recipient(s); default = config email_to")
    p.add_argument("--seed", default="", help="shared seed for per-game random starts (else fixed)")
    args = p.parse_args()
    asyncio.run(_run(args.opp_cop, args.opp_thief, args.grid_size, args.rounds, args.send,
                     args.email_to, args.seed))


if __name__ == "__main__":
    main()
