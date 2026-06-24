# TODO / Task Tracking — CopThief

Status legend: [x] done · [~] in progress · [ ] not started

## Phase 1 — Foundations (Level 1: local self-game)  ✅ complete
- [x] Scaffold uv project, ruff/pytest config, `.python-version` (3.12)
- [x] Versioned config files (`config.yaml`, `rate_limits.json`, `logging_config.json`)
- [x] Shared layer: config loader, version check, **audit logger**, API gatekeeper
- [x] Domain: models, board, rules, scoring, subgame state machine
- [x] LLM abstraction: base (Template Method), mock, Ollama, cloud API, Claude + factory
- [x] Dialogue (free NL announce/parse) + Agent + match setup
- [x] MatchRunner self-play pipeline with full audit logging
- [x] SDK facade + CLI (`selfplay`, `serve`, `serve-combined`, `netplay`)
- [x] JSON report builders (internal + bonus) + Gmail emailer
- [x] GUI: final-board PNG, per-subgame filmstrips, live ASCII board
- [x] Tests ≥ 85% coverage (currently ~96%), ruff clean, files ≤ 150 lines

## Phase 2 — Partial observation, strategy & deception  ✅ complete
- [x] Partial observation (`vision_radius`, `disclosure`) — DecPOMDP belief model
- [x] Strategies: adaptive (anticipation) + heuristic + tabular Q-learning + factory
- [x] Blind-search **hunt** (cop: last-seen → corner sweep); **evasion** (thief: open cells)
- [x] **Deception** (thief lies via mirror-decoy) + **counter-intelligence** (cop distrusts a proven liar)
- [x] Agent-level rule negotiation (vision radius); per-subgame state reset
- [x] Regenerated demo assets (board + 6 filmstrips + transcript) on seed 3

## Phase 3 — Cloud deployment (Level 2: self-game in the cloud)  ✅ code complete
- [x] FastMCP cop/thief servers over HTTP with token auth
- [x] Networked orchestrator (`mcp_client.NetworkMatch`) driving remote servers
- [x] `serve-combined` single-endpoint mode + persistent MCP sessions
- [x] Cloudflare quick tunnel verified end-to-end (full 6-subgame `netplay`)
- [x] Install `cloudflared`; local combined-mode proof (`tasks.ps1 cloud`)
- [ ] Run one **public** self-game over the named tunnel (`tasks.ps1 tunnel` → `netplay`)
- [x] Persistent host: named Cloudflare tunnel → `mcp.alon.website` (configured)

## Phase 4 — Inter-group bonus (Level 3)  ⏳ partner run scheduled for tomorrow
- [x] Agent-level rule negotiation built (vision radius); enhancements only by mutual agreement (§12)
- [x] Bonus JSON report (§9.2) builder + Gmail emailer ready
- [x] Shared-assumptions spec to send partner teams → `docs/BONUS_ASSUMPTIONS.md`
- [x] Peer-interop adapter (`interop/`: `deliver_message` + commit-reveal + canonical report) → `docs/PRD_interop.md`
- [ ] Pick partner team; exchange bearer tokens + 4 MCP URLs; smoke-test connectivity
- [ ] Wire the peer turn-loop to the partner's live agent (final remote step on game day)
- [ ] Run 6 subgames (3 as cop, 3 as thief); both teams email **matching** reports (else 0, §12.2)

## Submission checklist
- [x] Team identity in `config/config.yaml` (group `anrbj666`, students, repo)
- [x] Scientific report = `README.md` at the repo root (PDF §11) — no PDF export needed
- [x] Regenerate assets: `uv run python scripts/capture_demo.py` (per-subgame filmstrips)
- [ ] Record demo video (live game with Claude — see capture command below)
- [x] Gmail: confirmed delivery — `selfplay --email --email-to ...` sent the JSON report
- [x] Anthropic API key: kept **disabled** in the console except during active testing (the
      Claude CLI subscription is the primary path; the API key is only a fallback)

## Software-excellence compliance (guidelines V3 — §17 final checklist)
- [x] **Docs**: README (user manual + report), PRD (KPIs), PLAN (C4 + 6 ADRs), TODO, PRD_strategy, PROMPTS (§2)
- [x] **Code**: modular, files ≤150 lines, docstrings explain *why*, consistent style (§3)
- [x] **Architecture**: single SDK entry point; OOP + Template Method, no duplication (§4)
- [x] **API gatekeeper**: per-minute **and** per-hour throttle, retries, `get_queue_status` (§5)
- [x] **Testing**: TDD, ≥85% coverage (~96%), edge cases + graceful errors (§6)
- [x] **Quality/config/security**: ruff 0 errors, no hardcoded values, `.env.example`, secrets git-ignored (§7)
- [x] **Versioning & uv**: `version.py` 1.0.0 + config version validated on startup; uv only + `uv.lock` (§8)
- [x] **Research**: sensitivity sweep + analysis notebook + visualizations (§9)
- [x] **UI/UX & cost**: Nielsen heuristics + screenshots; token usage + cost analysis (§10/§11)
- [x] **Extensibility & standards**: strategy/LLM factories as extension points; ISO/IEC 25010 mapping (§12/§13)
