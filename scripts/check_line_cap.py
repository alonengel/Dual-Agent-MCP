"""Fail with exit code 1 if any Python file under src/, scripts/ or tests/ exceeds 150 lines.

The submission guideline (section 3.2) sets a hard 150-line cap per source file. This script
enforces it identically from the pre-commit hook and the GitHub Actions CI workflow, so the
rule is checked the same way locally and in CI.

Run directly:  python scripts/check_line_cap.py
"""
from __future__ import annotations

import pathlib
import sys

LIMIT = 150
ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRS = ("src", "scripts", "tests")


def main() -> int:
    bad: list[tuple[int, pathlib.Path]] = []
    for name in DIRS:
        for path in (ROOT / name).rglob("*.py"):
            with path.open("r", encoding="utf-8") as handle:
                n_lines = sum(1 for _ in handle)
            if n_lines > LIMIT:
                bad.append((n_lines, path))

    if bad:
        print(f"Files exceed the {LIMIT}-line cap (submission guideline section 3.2):")
        for n_lines, path in sorted(bad, reverse=True):
            print(f"  {n_lines:5}  {path.relative_to(ROOT)}")
        return 1
    print(f"All source files are at most {LIMIT} lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
