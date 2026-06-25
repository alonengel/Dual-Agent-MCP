"""CLI subcommand handlers, kept separate so main.py stays a thin parser/dispatcher.

Each ``run_*`` function takes the parsed argparse namespace and returns an exit code.
Heavy imports stay local to each handler so ``copthief --help`` is instant.
"""

from __future__ import annotations

import argparse
import functools

from copthief.constants import Role


def _email_report(sdk, path, subject: str, to_addr: str | None = None) -> None:
    """Email the report. PDF section 9: the body must be ONLY the structured JSON.

    ``to_addr`` overrides the configured course recipient (handy for testing).
    """
    import json

    from copthief.reporting.emailer import send_report_email

    report = json.loads(path.read_text(encoding="utf-8"))
    recipient = to_addr or sdk.config.get("reporting.email_to", "")
    send_report_email(recipient, subject, report, gate=sdk.gate)


def _board_renderer(args: argparse.Namespace):
    """Pick the per-turn board hook: live graphical window, ASCII, or none."""
    if args.animate:
        from copthief.gui.window import LiveWindow

        return LiveWindow()
    if args.verbose:
        from copthief.gui.live import render_live

        return render_live
    return None


def run_selfplay(args: argparse.Namespace) -> int:
    """Run a self-play match, save the report, optionally render/email it."""
    from copthief.sdk import CopThiefSDK

    sdk = CopThiefSDK(seed=args.seed)
    reporter = functools.partial(print, flush=True) if args.verbose else None
    board = _board_renderer(args)
    if hasattr(board, "run_match"):
        # Live window: run the match on a worker thread so the GUI stays responsive
        # (the event loop keeps pumping while a turn blocks on a slow LLM call).
        match = board.run_match(sdk, args.games, reporter)
    else:
        match = sdk.run_self_play(games=args.games, reporter=reporter, board_render=board)
    path = sdk.report_and_save(match)
    print(f"Totals: {match['totals']}\nReport: {path}")

    if hasattr(board, "close"):
        board.close()  # keep the live window open on its final frame
    if args.gui:
        from copthief.gui.viewer import render_audit

        render_audit(sdk.audit.path, sdk.config.root)
    if args.email:
        _email_report(sdk, path, "CopThief self-game report", args.email_to)
    return 0


def run_replay(args: argparse.Namespace) -> int:
    """Animate a recorded game from the audit log (window and/or saved GIF)."""
    from pathlib import Path

    from copthief.gui.animate import animate_audit
    from copthief.sdk import CopThiefSDK

    sdk = CopThiefSDK()
    audit_path = Path(args.audit) if args.audit else sdk.audit.path
    gif = animate_audit(audit_path, sdk.config.root, save_gif=args.save_gif,
                        show=not args.no_show, interval=args.interval)
    print(f"Replayed {audit_path}" + (f"\nGIF: {gif}" if gif else ""))
    return 0


def run_netplay(args: argparse.Namespace) -> int:
    """Run a match by driving the two MCP servers over HTTP (must be running)."""
    from copthief.sdk import CopThiefSDK

    sdk = CopThiefSDK(seed=args.seed)
    match = sdk.run_network_match()
    path = sdk.report_and_save(match)
    print(f"Totals: {match['totals']}\nReport: {path}")
    if args.email:
        _email_report(sdk, path, "CopThief inter-group game report", args.email_to)
    return 0


def run_serve(args: argparse.Namespace) -> int:
    """Start the cop or thief MCP server over HTTP."""
    from copthief.agents.server import run_server

    run_server(Role(args.role))
    return 0


def run_serve_combined(args: argparse.Namespace) -> int:
    """Start both agents under one HTTP endpoint (/cop/mcp and /thief/mcp)."""
    from copthief.agents.combined import run_combined

    run_combined()
    return 0
