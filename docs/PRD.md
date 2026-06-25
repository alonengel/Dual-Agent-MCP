# Product Requirements Document — CopThief

## 1. Overview & Context

CopThief implements **Exercise 6**: a complete, end-to-end pipeline in which two
autonomous AI agents — a **Cop** and a **Thief** — play a grid pursuit game while
communicating in **free natural language** over **MCP servers**. The agents set up
their own protocol by negotiating; an MCP-client orchestrator drives the match.

- **User / actor:** the course staff (grader) and partner teams in the bonus round.
- **Problem:** demonstrate orchestration of multi-agent, partially-observable systems
  with real-time decision-making and natural-language coordination.
- **Primary value:** a *working pipeline* (the headline grading criterion). Game
  strategy is explicitly secondary.

## 2. Goals & Success Metrics (KPIs / acceptance criteria)

| KPI | Target |
|-----|--------|
| Full self-game runs to completion | 6 valid subgames, scores aggregated |
| Two MCP servers reachable over HTTP | cop + thief, token-protected |
| State-by-state audit log produced | one line per turn, dispute-ready |
| JSON report generated & emailable | matches PDF sections 9.1 / 9.2 |
| Test coverage | ≥ 85% (achieved ~96%, 208 tests) |
| Files ≤ 150 lines, ruff clean, uv-managed | enforced |

**Acceptance:** `uv run copthief selfplay` produces a scored result, a saved JSON
report and an audit log; `uv run pytest --cov` passes ≥ 85%; `uv run ruff check .`
is clean.

## 3. Functional Requirements

- **FR1 — Game engine:** configurable grid (2×2…N×N), 25-move subgames, 6-subgame
  match, turn-based (thief first), 8-direction movement, cop barriers (max 5).
- **FR2 — Scoring:** cop win 20/5, thief win 10/5; max 90, min 30; bonus 10/7/5.
- **FR3 — Two MCP servers:** cop and thief each a FastMCP server over HTTP, exposing
  tools (`agree_protocol`, `play_turn`) with token auth + revocation.
- **FR4 — Natural-language dialogue:** agents exchange free text; the LLM verbalises
  intent and interprets the rival's message (no rigid wire protocol).
- **FR5 — LLM abstraction:** mock (offline), Ollama (local), cloud API.
- **FR6 — Audit logging:** append-only JSON-lines log of every state transition.
- **FR7 — Reporting:** internal + inter-group JSON reports, Gmail-API delivery.
- **FR8 — GUI:** board visualization rendered from the audit log.

## 4. Non-Functional Requirements

- **Security:** secrets only via env; MCP token revocable; no keys in source.
- **Performance:** a self-game completes in well under a second with the mock LLM.
- **Maintainability:** SDK-layered architecture, ≤150-line files, OOP/DRY, ruff.
- **Reliability:** technical-loss subgames are re-runnable; email never crashes the run.

## 5. User Stories

- *As a grader*, I run one command and see a working 6-subgame match with a saved
  report and an audit trail, so I can verify the pipeline.
- *As a partner team*, I point my orchestrator at the opponent's two MCP URLs and
  play 6 subgames autonomously, then both sides email matching JSON reports.
- *As a developer*, I swap the LLM provider via config/env without code changes.

## 6. Assumptions, Dependencies, Out of Scope

- **Assumptions:** Python 3.11–3.12; `uv` available; optional Ollama / API keys.
- **Dependencies:** FastMCP, httpx, NumPy, Matplotlib, Google API client.
- **Out of scope:** production cloud hosting hardening; full RL training pipeline
  (a tabular Q-learning option is provided but not trained to optimality).

## 7. Timeline & Milestones

1. Domain engine + tests → 2. Shared infra (config/log/gatekeeper) → 3. LLM + dialogue
→ 4. Self-play pipeline → 5. MCP servers + networked client → 6. Reporting + GUI →
7. Docs + coverage. (The bonus must be submitted within one week of release.)
