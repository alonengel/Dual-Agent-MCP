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
- [x] Tests ≥ 85% coverage (achieved 97%), ruff clean, files ≤ 150 lines

## Phase 2 — Level 2: cloud deployment (self-game in the cloud)
- [x] FastMCP cop/thief servers over HTTP with token auth (code complete)
- [x] Networked orchestrator (`mcp_client.NetworkMatch`) driving remote servers
- [ ] Deploy both MCP servers to a public host (Prefect Cloud / FastMCP host)
- [ ] Configure tokenized HTTPS URLs; verify firewall/DNS reachability
- [ ] Wire LLM in cloud (API key) or expose local Ollama via ngrok/Localtonet

## Phase 3 — Level 3: inter-group bonus (one-week deadline)
- [ ] Agree on partner team + shared assumptions over WhatsApp
- [ ] Exchange tokens + 4 MCP URLs; run 6 subgames (3 as cop, 3 as thief)
- [ ] Optional: negotiate enhanced rules at the **agent** level (more barriers, etc.)
- [ ] Both teams email matching bonus JSON reports (mutual agreement required)

## Cross-cutting (definition of done per item: tested + ruff-clean + ≤150 lines)
- [x] No hardcoded game parameters (all in config)
- [x] No secrets in source; `.env.example` with placeholders; `.gitignore` updated
- [x] Mandatory docs: PRD, PLAN, TODO, PRD_strategy, README
- [ ] Prompt-engineering log (`docs/PROMPTS.md`) — to be appended during development
- [ ] Results analysis notebook + parameter-sweep visualizations (enhancement)
