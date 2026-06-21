# CopThief — Dual AI Agents Pursuit Game over MCP Servers

> Course exercise 6 ("Orchestration of AI Agents", University of Haifa).
> Two autonomous AI agents — a **Cop** and a **Thief** — negotiate in free natural
> language and play a grid pursuit game. Each agent runs as its own **MCP server**
> (FastMCP) over HTTP; an MCP-client **orchestrator** owns the LLM and drives the match.

The headline grading criterion (per the lecture) is **a working end-to-end pipeline**:
two AI agents that set up a protocol by themselves and play. Strategy is secondary.

---

## Features

- **Domain engine**: 5×5 (configurable 2×2…N×N) grid, 25-move subgames, 6-subgame match,
  turn-based play (thief first), cop barriers (max 5), full scoring table.
- **Two MCP servers** (cop + thief) built with FastMCP, exposed over **HTTP even locally**
  (to prepare for the cloud step), protected by an auth **token** that can be revoked.
- **LLM abstraction**: `mock` (offline, deterministic — used for tests/CI), `claude`
  (Claude CLI with Anthropic-API fallback), `ollama` (local), and `api`
  (OpenAI / Anthropic / Gemini). All calls go through an API gatekeeper.
- **Critical audit logging**: every state transition is written to an append-only
  JSON-lines log — the evidence trail for inter-group dispute resolution.
- **Reporting**: builds the required internal / bonus **JSON report** and emails it via the
  **Gmail API** (token-based OAuth).
- **GUI**: renders the board, agents and barriers for visual proof.
- **Optional strategy**: heuristic decision-making + a tabular **Q-learning** option.

## Requirements

- Python **3.11–3.12** (the repo pins 3.12 via `.python-version`).
- [`uv`](https://docs.astral.sh/uv/) package manager (**mandatory** — no `pip`/`venv`).

## Installation

```bash
uv sync                 # creates .venv and installs locked dependencies
cp .env.example .env    # then edit .env (choose LLM provider, set token)
```

## Usage

```bash
# 1) Run a full local self-game (6 subgames) with the offline mock LLM:
uv run copthief selfplay

# 2) Same, rendering the GUI board:
uv run copthief selfplay --gui

# 3) Start the two MCP servers over HTTP (separate terminals):
uv run copthief serve --role cop
uv run copthief serve --role thief

# 4) With both servers running, drive a networked match (MCP-over-HTTP):
uv run copthief netplay --seed 7

# ...or do steps 3+4 with one command (starts servers, plays, cleans up):
powershell -File scripts/run_local_cloud.ps1

# 5) Run the test suite / analysis notebook:
uv run pytest --cov
uv run jupyter lab    # open notebooks/analysis.ipynb
```

> The networked path requires a shared token: set `COPTHIEF_MCP_TOKEN` to the same
> value for the servers and the orchestrator (the helper script sets a dev default).

A small task runner wraps the common commands:

```bash
powershell -File tasks.ps1 setup   # uv sync
powershell -File tasks.ps1 lint    # ruff check
powershell -File tasks.ps1 cov     # pytest with coverage
powershell -File tasks.ps1 selfplay
powershell -File tasks.ps1 demo    # capture board snapshot + move-by-move filmstrip
```

To run with **real Claude** (free language via the Claude CLI, Anthropic-API fallback),
set `COPTHIEF_LLM_PROVIDER=claude` in `.env` (see `.env.example`), then run `selfplay`.

Start small (`grid_size: [2, 2]` in `config/config.yaml`) to "flush the pipeline",
then scale up to 5×5 — this mirrors the staged sanity-check approach from the assignment.

## Configuration

All tunable parameters live in `config/` (never hardcoded in source):

| File | Purpose |
|------|---------|
| `config/config.yaml` | Game rules, scoring, MCP URLs, LLM + team settings (versioned) |
| `config/rate_limits.json` | API gatekeeper limits (versioned) |
| `config/logging_config.json` | Logging + audit-log configuration |
| `.env` | Secrets only (API keys, MCP token) — git-ignored |

## Project layout

```
src/copthief/
  sdk/            single entry point for all logic (SDK layer)
  domain/         board, rules, scoring, subgame state machine, models
  strategy/       heuristic + tabular Q-learning decision making
  llm/            provider abstraction (mock/ollama/api)
  agents/         FastMCP cop & thief servers + tool logic
  orchestrator/   MCP client + match runner (drives the 6-subgame dialogue)
  reporting/      JSON report builder + Gmail emailer
  shared/         config, logging/audit, version, API gatekeeper
  gui/            board viewer
docs/             PRD.md, PLAN.md, TODO.md, PRD_strategy.md
config/  tests/  results/  logs/  assets/
```

## Documentation

See [`docs/PRD.md`](docs/PRD.md), [`docs/PLAN.md`](docs/PLAN.md),
[`docs/TODO.md`](docs/TODO.md), [`docs/PRD_strategy.md`](docs/PRD_strategy.md),
[`docs/PROMPTS.md`](docs/PROMPTS.md) and [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
(cloud + inter-group bonus setup).

## Security

- No secrets in source: keys come from environment variables only; `.env` is git-ignored
  and `.env.example` ships placeholder values.
- The MCP server URL requires a token; revoke/rotate it to cut off third-party access.

## License & Credits

MIT License. Assignment authored by Dr. Yoram Segal. Built with FastMCP, NumPy,
Matplotlib and the Google API client.
