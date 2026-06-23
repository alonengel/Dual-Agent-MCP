"""Generate demo artifacts: run a self-game, then render boards + a transcript.

Writes to assets/:
  * board.png            - final board snapshot (single frame)
  * demo_filmstrip.png   - every move of the last subgame as a montage
  * demo_transcript.md   - the agents' natural-language dialogue, move by move

Usage:  uv run python scripts/capture_demo.py [--seed N]
"""

from __future__ import annotations

import argparse
import functools
import json
from pathlib import Path

from copthief.gui.live import render_live
from copthief.gui.sequence import render_frames
from copthief.gui.viewer import render_audit
from copthief.sdk import CopThiefSDK


def _write_transcript(audit_path: Path, out_dir: Path) -> Path:
    """Render the audit log's turn messages into a readable markdown transcript."""
    lines = ["# CopThief — agent dialogue transcript", ""]
    for raw in audit_path.read_text(encoding="utf-8").splitlines():
        e = json.loads(raw)
        if e.get("event") == "negotiation":
            if "## Protocol negotiation" not in lines:
                lines.append("## Protocol negotiation")
                lines.append("")
            lines.append(f"- **{e['role']}**: {e['message']}")
        elif e.get("event") == "subgame_start":
            lines.append(f"\n## Subgame {e['index']} (cop {tuple(e['cop'])}, "
                         f"thief {tuple(e['thief'])})\n")
        elif e.get("event") == "turn":
            lines.append(f"- **{e['role']}** (move {e['move']}): {e['message']}")
        elif e.get("event") == "subgame_end":
            lines.append(f"\n_Result: {e['outcome']} — cop {e['cop_score']}, "
                         f"thief {e['thief_score']}_")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "demo_transcript.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    """Run a seeded self-game and render the snapshot + filmstrip artifacts."""
    parser = argparse.ArgumentParser(description="Capture CopThief demo screenshots")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--games", type=int, default=None,
                        help="override subgame count (e.g. 2 for a short demo)")
    parser.add_argument("--quiet", action="store_true", help="suppress live dialogue output")
    args = parser.parse_args()

    sdk = CopThiefSDK(seed=args.seed)
    # Start from a clean audit log so the transcript/filmstrip reflect only this run.
    sdk.audit.path.write_text("", encoding="utf-8")
    reporter = None if args.quiet else functools.partial(print, flush=True)
    board = None if args.quiet else render_live
    match = sdk.run_self_play(games=args.games, reporter=reporter, board_render=board)
    sdk.report_and_save(match)

    root = sdk.config.root
    snapshot = render_audit(sdk.audit.path, root)
    filmstrip = render_frames(sdk.audit.path, root)
    transcript = _write_transcript(sdk.audit.path, root / "assets")
    print(f"totals: {match['totals']}")
    print(f"snapshot:   {snapshot}")
    print(f"filmstrip:  {filmstrip}")
    print(f"transcript: {transcript}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
