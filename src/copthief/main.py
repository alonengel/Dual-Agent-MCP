"""Command-line interface for CopThief (thin parser; handlers live in commands.py).

Subcommands:
  selfplay        run a full local self-game (the mandatory Level-1 pipeline)
  replay          animate a recorded game from the audit log (window and/or GIF)
  netplay         drive two running MCP servers over HTTP (inter-group play)
  serve           start a single agent's MCP server over HTTP
  serve-combined  serve both agents under one endpoint (/cop/mcp, /thief/mcp)
"""

from __future__ import annotations

import argparse
import sys

from copthief import commands
from copthief.constants import Role


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse CLI parser."""
    parser = argparse.ArgumentParser(prog="copthief", description="Dual AI agents pursuit game")
    sub = parser.add_subparsers(dest="command", required=True)

    play = sub.add_parser("selfplay", help="run a local self-game")
    play.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    play.add_argument("--gui", action="store_true", help="render the board from the audit log")
    play.add_argument("--email", action="store_true", help="email the JSON report via Gmail")
    play.add_argument("--email-to", default=None, help="override report recipient (testing)")
    play.add_argument("--games", type=int, default=None, help="override subgame count (demo)")
    play.add_argument("--verbose", action="store_true", help="print agent dialogue live")
    play.add_argument("--animate", action="store_true",
                      help="show a live graphical window of the board as agents move")
    play.set_defaults(func=commands.run_selfplay)

    replay = sub.add_parser("replay", help="animate a recorded game from the audit log")
    replay.add_argument("--audit", default=None, help="audit log path (default: configured log)")
    replay.add_argument("--save-gif", action="store_true", help="write assets/demo_animation.gif")
    replay.add_argument("--no-show", action="store_true", help="don't open a window (GIF only)")
    replay.add_argument("--interval", type=int, default=700, help="ms per move frame")
    replay.set_defaults(func=commands.run_replay)

    net = sub.add_parser("netplay", help="run a match against running MCP servers")
    net.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    net.add_argument("--email", action="store_true", help="email the JSON report via Gmail")
    net.add_argument("--email-to", default=None, help="override report recipient (testing)")
    net.set_defaults(func=commands.run_netplay)

    serve = sub.add_parser("serve", help="start an agent MCP server")
    serve.add_argument("--role", choices=[r.value for r in Role], required=True)
    serve.set_defaults(func=commands.run_serve)

    combined = sub.add_parser("serve-combined",
                              help="serve both agents on one endpoint (/cop/mcp, /thief/mcp)")
    combined.set_defaults(func=commands.run_serve_combined)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the selected subcommand."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
