# CopThief — Dual AI Agents Pursuit Game over MCP Servers

> Course exercise 6 ("Orchestration of AI Agents", University of Haifa).
> Two autonomous AI agents — a **Cop** and a **Thief** — negotiate in free natural
> language and play a grid pursuit game. Each agent runs as its own **MCP server**
> (FastMCP) over HTTP; an MCP-client **orchestrator** owns the LLM and drives the match.

The headline grading criterion (per the lecture and PDF §3) is **a working end-to-end
pipeline**: two AI agents that set up a protocol by themselves and play. Strategy is
secondary. **This README doubles as the assignment's scientific report (PDF §11).**

---

## 1. Problem framing — a DecPOMDP

The pursuit is a **Decentralized, Partially Observable Markov Decision Process**, formally
`⟨ n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ ⟩`:

| Symbol | Meaning in CopThief |
|--------|---------------------|
| `n` | 2 agents — cop and thief |
| `S` | board state: both positions + the set of barrier cells |
| `{Aᵢ}` | per-agent actions: move in 8 directions, `STAY`, or (cop only) place a barrier |
| `P` | deterministic transition (referee applies a legal move; illegal → no-op) |
| `R` | the scoring table (cop_win 20 / thief_win 10 / loss 5) |
| `{Ωᵢ}, O` | each agent observes only its own cell + the rival's *messages*; the rival's exact cell is revealed **only within a Chebyshev `vision_radius`** |
| `γ` | discount (conceptual; play is finite-horizon at 25 moves) |

Partial observability is the crux: beyond the vision radius an agent acts on a **belief**
formed from the opponent's free-text messages — which may be vague, stale, or **deceptive**.

## 2. System architecture

```
            ┌──────────────────────── MCP client / orchestrator ─────────────────────────┐
            │  owns the LLM (per PDF §5.2)  ·  runs each agent persona  ·  referee+audit   │
            │   Agent(cop)  ── decide → verbalise → parse ──  Agent(thief)                 │
            └──────────┬──────────────────────────────────────────────┬──────────────────┘
                       │ MCP-over-HTTP (Bearer token)                  │
              ┌────────▼────────┐                            ┌─────────▼────────┐
              │ Cop MCP server  │  pure tools:               │ Thief MCP server │
              │ (FastMCP)       │  reset/observe/move/...     │ (FastMCP)        │
              └─────────────────┘                            └──────────────────┘
```

- **LLM lives in the client, not the servers** (PDF §5.2): servers expose *pure tools*
  (`reset`, `observe`, `move`, `place_barrier`, `note`); the orchestrator runs the LLM
  persona, decides, verbalises, parses the reply, and calls the tools.
- **Security**: transport-level **bearer-token** auth on every call (revoke by rotating
  the token; wrong/absent token → 401). Secrets only via environment / `.env`.
- **Reliability**: all external LLM/Gmail calls route through an **API gatekeeper**
  (rate-limit + retry) and a **token-usage meter** (cost estimate per model).
- **Auditability**: every negotiation message, turn and outcome is appended to a
  JSON-lines **audit log** — the evidence trail for inter-group dispute resolution.

## 3. Free-language orchestration & partial observation (the core challenge)

- **No rigid protocol** (PDF §5.1): each turn an agent emits a free-text message describing
  its **intentions, local observations, or attempts at deception** — *not* raw coordinates.
  A tolerant parser extracts a cell only when one is volunteered.
- **Conditional disclosure**: under `disclosure: partial`, an agent reveals its `(x,y)`
  **only when the rival can already see it**; otherwise it gives a vague direction. The
  opponent's belief then goes stale and it must **search** to re-acquire.
- **Deception** (thief): when unseen, the thief **lies** — it claims the mirror-image cell
  to lure the pursuer to the far side of the board.
- **Counter-intelligence** (cop): the cop treats a stated cell as a single *unverified
  lead*. On reaching it to find nobody, it concludes it was deceived and **ignores that
  liar's claims** for the rest of the subgame, falling back on sight + systematic search.
- **The hunt**: a blind cop does not idle — it heads to the thief's **last-seen** cell, then
  **sweeps the board corners**; the thief flees toward **open, central** cells to avoid
  being cornered. This is what makes the cop competent under partial observation.

## 4. Strategy (secondary)

- **Adaptive (default)** anticipates the rival's next cell from its last move; **heuristic**
  is greedy Chebyshev distance with cornering (cop) / open-cell (thief) tie-breaks;
  **tabular Q-learning** is an optional learning policy (ε-greedy, Bellman update).
- **Barriers** are *need-based* (≤5/subgame): the cop blocks only when genuinely boxed in.
  On an open 5×5 with own-cell placement they are rarely the best move, so they stay a
  situational tool rather than a core tactic.

## 5. Results & visualizations (proofs)

The cop's active search makes pursuit **board-size sensitive** under `vision_radius: 1`
(competent cop vs. evading thief; 90 subgames/size). This is a **sensitivity study — the
game is played on `5×5`** (PDF §4.2/§10 default); `2×2 → 4×4` are the §4.5 sanity stages.

| Board | 5×5 | 6×6 | 7×7 | 8×8 | 9×9 |
|-------|-----|-----|-----|-----|-----|
| **Cop win %** | 93 | 82 | 72 | 57 | 47 |

With thief **deception** + a skeptical cop enabled (the default), 5×5 settles at ~**87% cop**
— the thief's lies lift its share, but counter-intelligence keeps the cop ahead. Quality
bar: **106 tests, 93% coverage**, ruff-clean, every source file ≤150 lines.

**Visual proof** — three complementary views. The **live CLI** (`selfplay --verbose`) prints
the board and the agents' free-language dialogue every turn (here the thief *lies* and the
cop sees through it):

```text
[negotiate] cop: Let's play 5x5, origin 1 — you move first, agreed?
[negotiate] thief: Agreed, 5x5 and I lead.

== Subgame 1 | cop (4,5) vs thief (2,3)
  thief m0: Drifting west into the open — catch me at (5,3) if you can.   # decoy: really (2,3)
 5 . . . C .
 4 . . . . .
 3 T . . . .
 2 . . . . .
 1 . . . . .
   1 2 3 4 5
  cop  m1: I don't buy it — sweeping the board to flush you out.
   ... (capture at move 13)
   -> cop_win (cop 20, thief 5)
```

A **final-state PNG** and a **move-by-move filmstrip per subgame** complete the picture:

![Final board](assets/board.png)

![Subgame 1, move by move](assets/demo_filmstrip_sg1.png)

The full set `assets/demo_filmstrip_sg1.png … sg6.png` and the dialogue transcript
`assets/demo_transcript.md` are regenerated by `scripts/capture_demo.py`. The board-size
sweep is reproducible in `notebooks/analysis.ipynb`.

---

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
# Local self-game (6 subgames) with the offline mock LLM:
uv run copthief selfplay

# Live demo — natural-language dialogue + ASCII board each turn, then a final PNG
# (set COPTHIEF_LLM_PROVIDER=claude in .env for real Claude):
uv run copthief selfplay --verbose --gui --seed 3

# Networked play — combined server (recommended for tunnels) then drive a match:
uv run copthief serve-combined          # /cop/mcp and /thief/mcp on :8080
uv run copthief netplay --seed 7

# One-command local "cloud" run (starts servers, plays, cleans up):
powershell -File scripts/run_local_cloud.ps1

# Email the JSON report (use --email-to to test against your own inbox first):
uv run copthief selfplay --email --email-to you@example.com

# Tests with coverage / the analysis notebook:
uv run pytest --cov
uv run jupyter lab    # open notebooks/analysis.ipynb
```

> The networked path needs a shared token: set `COPTHIEF_MCP_TOKEN` to the same value for
> the servers and the orchestrator (the helper script sets a dev default). For a free public
> URL, use `powershell -File tasks.ps1 cloud` (serve-combined + Cloudflare tunnel) — see
> [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

Start small (`grid_size: [2, 2]`) to "flush the pipeline", then scale to 5×5 — the staged
sanity-check approach from PDF §4.5.

## Configuration

All tunable parameters live in `config/` (never hardcoded):

| File | Purpose |
|------|---------|
| `config/config.yaml` | Game rules, scoring, partial-observation, MCP URLs, LLM + team settings |
| `config/rate_limits.json` | API gatekeeper limits |
| `config/logging_config.json` | Logging + audit-log configuration |
| `.env` | Secrets only (API keys, MCP token) — git-ignored |

## Project layout

```
src/copthief/
  sdk/            single entry point for all logic (SDK layer)
  domain/         board, rules, scoring, subgame state machine, models
  strategy/       adaptive + heuristic + tabular Q-learning decision making
  llm/            provider abstraction (mock/claude/ollama/api) via API gatekeeper
  agents/         FastMCP cop & thief servers exposing pure tools (no LLM, per PDF §5.2)
  orchestrator/   MCP client (owns the LLM) + match runner: hunt, deception, counter-intel
  reporting/      JSON report builder + Gmail emailer
  shared/         config, logging/audit, version, API gatekeeper, token-usage meter
  gui/            live ASCII board + final-board viewer + per-subgame filmstrips
docs/             PRD.md, PLAN.md, TODO.md, PRD_strategy.md, PROMPTS.md, DEPLOYMENT.md
config/  tests/  results/  logs/  assets/  notebooks/
```

## Documentation

[`docs/REPORT.md`](docs/REPORT.md) is an extended companion to this report;
[`docs/PRD.md`](docs/PRD.md), [`docs/PLAN.md`](docs/PLAN.md) (architecture/ADRs),
[`docs/PRD_strategy.md`](docs/PRD_strategy.md), [`docs/PROMPTS.md`](docs/PROMPTS.md)
(prompt-engineering log), and [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) (cloud +
inter-group bonus setup) cover the rest.

## Security

- No secrets in source: keys come from environment variables only; `.env` is git-ignored
  and `.env.example` ships placeholder values.
- The MCP servers require a bearer token; revoke/rotate it to cut off third-party access.

## Contributing

- Use **uv** for everything (`uv sync`, `uv run ...`); never `pip`/`venv` directly.
- Keep every source file **≤ 150 lines**; one responsibility per module.
- Add/adjust tests under `tests/`, keep coverage **≥ 85%** (`uv run pytest --cov`).
- Code must pass **`uv run ruff check .`** with zero errors; docstrings explain *why*.
- No hardcoded config or secrets. Run `powershell -File tasks.ps1 all` before a PR.

## License & Credits

MIT License. Assignment authored by Dr. Yoram Segal. Built with FastMCP, NumPy,
Matplotlib and the Google API client.
