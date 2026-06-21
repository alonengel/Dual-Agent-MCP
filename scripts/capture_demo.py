"""Generate demo screenshots: run a self-game, then render the board artifacts.

Writes to assets/:
  * board.png          - final board snapshot (single frame)
  * demo_filmstrip.png - every move of the last subgame as a montage

Usage:  uv run python scripts/capture_demo.py [--seed N]
"""

from __future__ import annotations

import argparse

from copthief.gui.sequence import render_frames
from copthief.gui.viewer import render_audit
from copthief.sdk import CopThiefSDK


def main() -> int:
    """Run a seeded self-game and render the snapshot + filmstrip artifacts."""
    parser = argparse.ArgumentParser(description="Capture CopThief demo screenshots")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    sdk = CopThiefSDK(seed=args.seed)
    match = sdk.run_self_play()
    sdk.report_and_save(match)

    root = sdk.config.root
    snapshot = render_audit(sdk.audit.path, root)
    filmstrip = render_frames(sdk.audit.path, root)
    print(f"totals: {match['totals']}")
    print(f"snapshot:  {snapshot}")
    print(f"filmstrip: {filmstrip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
