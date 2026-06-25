# CLAUDE.md — working guide for this repo

CopThief: two autonomous AI agents (**Cop**, **Thief**) negotiate in free natural
language and play a partially-observable grid-pursuit game. Each agent is its own
**MCP server** (FastMCP/HTTP); an MCP-client **orchestrator** owns the LLM and
referees. Built for UoH Exercise 6. The README doubles as the scientific report.

## Golden rules (graded — do not break)

- **≤150 lines per `.py` file** under `src/`, `scripts/`, `tests/` (hard cap, PDF §3.2).
  If a file would grow past it, split by responsibility — never compress to dodge it.
  Enforced by `scripts/check_line_cap.py`, pre-commit, and CI.
- **Nothing hardcoded.** All tunables live in `config/config.yaml` (+ `rate_limits.json`,
  `logging_config.json`). Read via `Config` (dotted keys). No magic game numbers in code.
- **SDK is the single entry point.** External consumers (CLI, scripts, GUI) call
  `copthief.sdk.CopThiefSDK`; they never reach into internal modules for business logic.
- **OOP, DRY, one responsibility per module.** No copy-paste logic across files.
- **Ruff must be clean** (`uv run ruff check .`, zero violations) and **coverage ≥85%**.
- **No secrets in git.** `.env`, `credentials.json`, `token.json` are git-ignored; commit
  only `.env.example`.
- **uv only** — `uv run <cmd>`, `uv add <pkg>`. Never `pip`/`python -m` directly.

## Layout (src/copthief/)

| Package | Responsibility |
|---------|----------------|
| `domain/` | Pure game model: board, rules, subgame, scoring (no I/O) |
| `orchestrator/` | The referee/match loop, perception, negotiation, MCP client |
| `agents/` | FastMCP servers (cop, thief, combined endpoint) — tools only, no LLM |
| `llm/` | LLM providers: `mock` (offline default), `claude`, `ollama`, `api` |
| `strategy/` | Move strategies: lookahead (default, depth-1 minimax), adaptive, heuristic, Q-learning |
| `interop/` | Inter-group (bonus) adapter: messaging, commit-reveal, report hash |
| `reporting/` | JSON reports (§9.1/9.2) + Gmail emailer |
| `gui/` | Board rendering — see "GUI / matplotlib" below |
| `shared/` | Config, gatekeeper (rate-limit queue), usage meter, version, logging |
| `sdk/` | The façade used by everything external |

## Run / test / verify

```bash
uv sync                                   # install
uv run copthief selfplay --verbose        # local self-game, live ASCII board
uv run copthief selfplay --animate        # local self-game, live GRAPHICAL window
uv run copthief replay --save-gif --no-show   # animate the last game -> assets/demo_animation.gif
uv run python scripts/capture_demo.py     # regenerate all demo assets (PNG + GIF + transcript)
uv run pytest --cov                        # tests + coverage gate
uv run ruff check . && uv run python scripts/check_line_cap.py
uv run python scripts/check_submission.py  # one-shot rubric self-check (see below)
```

`COPTHIEF_LLM_PROVIDER=mock` is the offline default so nothing calls a real LLM. Tests
force it via `conftest.py`. Set provider to `claude`/`api`/`ollama` in `.env` for real runs.

## Submission gate

`scripts/check_submission.py` maps each grading-rubric item (line cap, ruff, coverage,
config completeness, versioning, docs, secrets, uv files, report schema, GUI artifacts)
to an automated check and prints a PASS/FAIL table. Run it before submitting; `--fast`
skips the pytest step.

## GUI / matplotlib gotcha

`gui/board_draw.py` is **backend-neutral on purpose**. Headless PNG/GIF generators
(`viewer.py`, `sequence.py`, `capture_demo.py`, tests) must call
`matplotlib.use("Agg")` *before* importing `pyplot`. The interactive window paths
(`animate.py` `replay`, `window.py` `--animate`) keep the default backend and degrade
to a no-op when no display is available, so they never crash CI.

## Conventions when editing

- Match the surrounding style; keep docstrings explaining **why**, not just what.
- New module → add a mirrored test under `tests/unit/` (or `tests/integration/`).
- Keep `domain/` pure (no file/network I/O); side effects belong in orchestrator/SDK.
- After changes: `ruff check .`, `pytest --cov`, `check_line_cap.py` must all pass.
