# TODO / Task Tracking — CopThief

Status legend: [x] done · [~] in progress · [ ] not started

## Phase 1 — Foundations (Level 1: local self-game)
- [x] Scaffold uv project, ruff/pytest config, `.python-version` (3.12)
- [x] Versioned config files (`config.yaml`, `rate_limits.json`, `logging_config.json`)
- [x] Shared layer: config loader, version check, **audit logger**, API gatekeeper
- [x] Domain: models, board, rules, scoring, subgame state machine
- [x] Strategy: heuristic + tabular Q-learning + factory
- [x] LLM abstraction: base, mock (offline), Ollama, cloud API + factory
- [x] Dialogue (free NL announce/parse) + Agent + match setup
- [x] MatchRunner self-play pipeline with full audit logging
- [x] SDK facade + CLI (`selfplay`, `serve`)
- [x] JSON report builders (internal + bonus) + Gmail emailer
- [x] GUI board viewer (audit-log → PNG)
- [x] Tests ≥ 85% coverage (currently 93%), ruff clean, files ≤ 150 lines

## Phase 2 — Level 2: cloud deployment (self-game in the cloud)
- [x] FastMCP cop/thief servers over HTTP with token auth (code complete)
- [x] Networked orchestrator (`mcp_client.NetworkMatch`) driving remote servers
- [x] `serve-combined` single-endpoint mode + persistent MCP sessions
- [x] Cloudflare quick tunnel verified end-to-end (full 6-subgame `netplay`)
- [x] Local combined-mode proof (`scripts/run_local_cloud.ps1`, `tasks.ps1 cloud`)
- [x] Install `cloudflared` on your machine (`winget install Cloudflare.cloudflared`)
- [ ] Run one public self-game: `tasks.ps1 cloud` → set tunnel URLs → `netplay`
- [ ] Optional: deploy to a persistent host (free VM + Caddy, or named Cloudflare tunnel)

## Phase 3 — Level 3: inter-group bonus (one-week deadline)
- [ ] Agree on partner team + shared assumptions over WhatsApp
- [ ] Exchange tokens + 4 MCP URLs; run 6 subgames (3 as cop, 3 as thief)
- [ ] Optional: negotiate enhanced rules at the **agent** level (more barriers, etc.)
- [ ] Both teams email matching bonus JSON reports (mutual agreement required)

## Submission checklist (individual + team)
- [x] Fill `config/config.yaml` → `team.group_name`, `team.students`, `team.github_repo`
- [ ] Record demo video: `uv run copthief selfplay --verbose --gui --seed 3` with `COPTHIEF_LLM_PROVIDER=claude`
- [x] Regenerate assets: `uv run python scripts/capture_demo.py` (per-subgame filmstrips)
- [ ] Gmail OAuth: place `credentials.json`, run `uv run copthief selfplay --email` once
- [x] Scientific report is `README.md` at the repo root (PDF §11) — no PDF export needed
- [ ] Rotate any exposed API keys (Anthropic key was in chat history)

## Cross-cutting (definition of done per item: tested + ruff-clean + ≤150 lines)
- [x] No hardcoded game parameters (all in config)
- [x] No secrets in source; `.env.example` with placeholders; `.gitignore` updated
- [x] Mandatory docs: PRD, PLAN, TODO, PRD_strategy, README
- [x] Prompt-engineering log (`docs/PROMPTS.md`)
- [x] Results analysis notebook + parameter-sweep visualizations (`notebooks/analysis.ipynb`)
- [x] One-command local "cloud" launcher (`scripts/run_local_cloud.ps1`) + `netplay` CLI
