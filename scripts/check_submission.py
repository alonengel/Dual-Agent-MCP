"""Submission gate: auto-check the repo against the course rubric in one command.

Maps each grading item from the two course PDFs (submission-guidelines final
checklist, sections 17 / 20.9, plus the exercise's concrete deliverables) to an
automated check and prints a PASS / FAIL / WARN table. Exit code is non-zero on any
FAIL, so this doubles as a pre-submission gate next to CI. The rubric section for
each check is shown in its row label.

Run:  uv run python scripts/check_submission.py [--fast]   (--fast skips pytest)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ["README.md", "docs/PRD.md", "docs/PLAN.md", "docs/TODO.md",
        "docs/PRD_strategy.md", "docs/PRD_interop.md", "docs/PROMPTS.md"]
CFG_KEYS = ["game.grid_size", "game.max_moves", "game.num_games", "game.max_barriers",
            "scoring.cop_win", "scoring.thief_win", "scoring.cop_loss", "scoring.thief_loss"]
REPORT_KEYS = {"group_name", "students", "github_repo", "cop_mcp_url", "thief_mcp_url",
               "timezone", "sub_games", "totals"}
PASS, FAIL, WARN = "PASS", "FAIL", "WARN"


def _sh(*cmd: str) -> tuple[int, str]:
    """Run a command from the repo root; return (exit code, last output line)."""
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    lines = (proc.stdout + proc.stderr).strip().splitlines()
    return proc.returncode, (lines[-1] if lines else "")


def _dig(data: dict, dotted: str):
    """Fetch a dotted key from nested dicts, or None if any hop is missing."""
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _yaml(rel: str) -> dict:
    """Load a YAML file under the repo root."""
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


def check_line_cap() -> tuple[str, str]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_line_cap import main as cap
    return (PASS, "all files <= 150 lines") if cap() == 0 else (FAIL, "see output above")


def check_ruff() -> tuple[str, str]:
    code, tail = _sh("uv", "run", "ruff", "check", ".")
    return (PASS, "0 violations") if code == 0 else (FAIL, tail)


def check_tests(fast: bool) -> tuple[str, str]:
    if fast:
        return WARN, "skipped (--fast)"
    code, tail = _sh("uv", "run", "pytest", "--cov", "-q")
    return (PASS, tail) if code == 0 else (FAIL, tail)


def check_config() -> tuple[str, str]:
    missing = [k for k in CFG_KEYS if _dig(_yaml("config/config.yaml"), k) is None]
    return (FAIL, f"missing {missing}") if missing else (PASS, "all game/scoring keys present")


def check_versioning() -> tuple[str, str]:
    cfg = _yaml("config/config.yaml")
    rl = json.loads((ROOT / "config/rate_limits.json").read_text(encoding="utf-8"))
    ok = cfg.get("version") and rl.get("version") and (
        ROOT / "src/copthief/shared/version.py").exists()
    return (PASS, f"config {cfg.get('version')}, rate_limits {rl.get('version')}") if ok \
        else (FAIL, "a version marker is missing")


def check_docs() -> tuple[str, str]:
    missing = [d for d in DOCS if not (ROOT / d).exists()]
    return (FAIL, f"missing {missing}") if missing else (PASS, f"{len(DOCS)} docs present")


def check_secrets() -> tuple[str, str]:
    _, out = _sh("git", "ls-files")
    leaked = [s for s in (".env", "credentials.json", "token.json") if s in out.split()]
    example = (ROOT / ".env.example").exists() or (ROOT / ".env-example").exists()
    if leaked:
        return FAIL, f"secrets tracked: {leaked}"
    return (PASS, "no secrets tracked; env template present") if example else (WARN, "no env template")


def check_packaging() -> tuple[str, str]:
    ok = (ROOT / "pyproject.toml").exists() and (ROOT / "uv.lock").exists()
    return (PASS, "pyproject.toml + uv.lock") if ok else (FAIL, "missing uv files")


def check_report_schema() -> tuple[str, str]:
    reports = sorted((ROOT / "results").glob("internal_*.json"))
    if not reports:
        return WARN, "no internal_*.json yet (run a self-game)"
    missing = REPORT_KEYS - set(json.loads(reports[-1].read_text(encoding="utf-8")))
    return (FAIL, f"missing {missing}") if missing else (PASS, f"schema ok ({reports[-1].name})")


def check_gui_artifacts() -> tuple[str, str]:
    png = (ROOT / "assets/board.png").exists()
    gif = (ROOT / "assets/demo_animation.gif").exists()
    if png and gif:
        return PASS, "board.png + demo_animation.gif"
    return (WARN, "board.png only; run capture_demo.py for the GIF") if png \
        else (FAIL, "no GUI artifacts (run capture_demo.py)")


def main(argv: list[str] | None = None) -> int:
    """Run every check and print a rubric table; exit non-zero on any FAIL."""
    fast = "--fast" in (argv if argv is not None else sys.argv[1:])
    checks = [
        ("150-line cap (3.2)", check_line_cap), ("Ruff lint (7.1)", check_ruff),
        ("Tests + coverage (6.2)", lambda: check_tests(fast)),
        ("Config complete (10)", check_config), ("Versioning (8.1)", check_versioning),
        ("Docs present (2.2)", check_docs), ("No secrets (7.4)", check_secrets),
        ("uv packaging (8.4)", check_packaging), ("Report schema (9.1)", check_report_schema),
        ("GUI artifacts (12)", check_gui_artifacts),
    ]
    rows = []
    for name, fn in checks:
        try:
            status, detail = fn()
        except Exception as exc:  # a broken check must not mask the others
            status, detail = FAIL, f"{type(exc).__name__}: {exc}"
        rows.append((status, name, detail))
    width = max(len(n) for _, n, _ in rows)
    print("\nCopThief submission gate\n" + "=" * 64)
    for status, name, detail in rows:
        print(f"  [{status}] {name.ljust(width)}  {detail}")
    print("=" * 64)
    failed = any(s == FAIL for s, _, _ in rows)
    print("RESULT:", "FAIL - fix the items above" if failed else "PASS - ready to submit")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
