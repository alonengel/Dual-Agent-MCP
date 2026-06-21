"""Command-line interface for CopThief.

Subcommands:
  selfplay   run a full local self-game (the mandatory Level-1 pipeline)
  serve      start a single agent's MCP server over HTTP
"""

from __future__ import annotations

import argparse
import sys

from copthief.constants import Role


def _selfplay(args: argparse.Namespace) -> int:
    """Run a self-play match, save the report, optionally render/email it."""
    from copthief.reporting.emailer import send_report_email
    from copthief.sdk import CopThiefSDK

    sdk = CopThiefSDK(seed=args.seed)
    match = sdk.run_self_play()
    path = sdk.report_and_save(match)
    print(f"Totals: {match['totals']}\nReport: {path}")

    if args.gui:
        from copthief.gui.viewer import render_audit

        render_audit(sdk.audit.path, sdk.config.root)
    if args.email:
        report = path.read_text(encoding="utf-8")
        send_report_email(sdk.config.get("reporting.email_to", ""),
                          "CopThief self-game report", {"report": report})
    return 0


def _netplay(args: argparse.Namespace) -> int:
    """Run a match by driving the two MCP servers over HTTP (must be running)."""
    from copthief.sdk import CopThiefSDK

    sdk = CopThiefSDK(seed=args.seed)
    match = sdk.run_network_match()
    path = sdk.report_and_save(match)
    print(f"Totals: {match['totals']}\nReport: {path}")
    return 0


def _serve(args: argparse.Namespace) -> int:
    """Start the cop or thief MCP server over HTTP."""
    from copthief.agents.server import run_server

    run_server(Role(args.role))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse CLI parser."""
    parser = argparse.ArgumentParser(prog="copthief", description="Dual AI agents pursuit game")
    sub = parser.add_subparsers(dest="command", required=True)

    play = sub.add_parser("selfplay", help="run a local self-game")
    play.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    play.add_argument("--gui", action="store_true", help="render the board from the audit log")
    play.add_argument("--email", action="store_true", help="email the JSON report via Gmail")
    play.set_defaults(func=_selfplay)

    net = sub.add_parser("netplay", help="run a match against running MCP servers")
    net.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    net.set_defaults(func=_netplay)

    serve = sub.add_parser("serve", help="start an agent MCP server")
    serve.add_argument("--role", choices=[r.value for r in Role], required=True)
    serve.set_defaults(func=_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the selected subcommand."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
