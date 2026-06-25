# Architecture & Plan — CopThief

## 1. C4 Overview

### Context
Two AI agents (Cop, Thief) coordinate over MCP to play a pursuit game. The grader
(or a partner team) runs the orchestrator; results are emailed to the course inbox.

### Containers
- **Orchestrator (MCP client + LLM)** — drives the match, referees authoritative
  state, writes the audit log, builds reports.
- **Cop MCP server** / **Thief MCP server** — FastMCP servers over HTTP exposing
  agent tools; each owns its strategy and LLM voice.
- **LLM** — mock / local Ollama / cloud API.
- **Reporting** — JSON builder + Gmail API.

### Components (per `src/copthief/`)
```
sdk/          facade: the single entry point for all consumers
domain/       board, rules, scoring, subgame state machine, models (pure, no I/O)
strategy/     heuristic + tabular Q-learning + factory
llm/          provider abstraction (base, mock, ollama, api) + factory
orchestrator/ dialogue, agent, setup, match (self-play), mcp_client (networked)
agents/       session (per-agent state) + FastMCP server
reporting/    report builders + Gmail emailer
shared/       config, logger/audit, gatekeeper, version
gui/          matplotlib board viewer
```

## 2. Key Flows

### Self-play turn (in-process pipeline)
1. Orchestrator builds the current role's **partial observation**.
2. Agent's **strategy** chooses a `Move` (belief-aware).
3. Referee `Subgame.apply()` **validates + mutates** state.
4. Agent's **LLM** verbalises the move → free-text message.
5. Opponent **parses** the message → updates belief.
6. **Audit log** records the full transition. Repeat until capture / 25 moves.

### Networked match (cloud / bonus)
The MCP **client** (orchestrator) owns the LLM. Per turn it builds the observation,
decides the move (strategy) and verbalises it (LLM), then calls the agent server's
**pure** tools over HTTP (token-authed) to execute: `reset`, `move`, `place_barrier`,
`note`, `observe`. The client is the authoritative referee; the servers hold no LLM.

## 3. Architecture Decision Records (ADRs)

Each decision is its own file under [`docs/adr/`](adr/README.md) (Status / Context /
Decision / Consequences), so decisions are versioned individually and never rewritten.

| ADR | Decision |
|-----|----------|
| [0001](adr/0001-sdk-facade.md) | Single SDK facade as the only entry point |
| [0002](adr/0002-llm-in-mcp-client.md) | The LLM lives only in the MCP client (PDF §5.2) |
| [0003](adr/0003-referee-authoritative-state.md) | The referee holds authoritative state |
| [0004](adr/0004-http-transport-local.md) | HTTP transport even for local play |
| [0005](adr/0005-mock-provider-first-class.md) | The mock LLM provider is first-class |
| [0006](adr/0006-config-driven.md) | Config-driven everything (no hardcoded parameters) |
| [0007](adr/0007-interop-additive-adapter.md) | Inter-group bonus is an additive peer adapter |
| [0008](adr/0008-probabilistic-belief-grid.md) | Probabilistic belief grid (partial observation) |
| [0009](adr/0009-deterministic-replay.md) | Deterministic replay of the audit log |

## 4. Interfaces / Contracts

- **MCP tools (pure, per agent server):** `reset(x,y,barriers_left)`, `observe()`,
  `move(dx,dy)`, `place_barrier()`, `note(message)`, `deliver_message(text)` (inter-group
  free-text channel) and `inbox()` (full ordered mailbox the peer loop polls) — no LLM inside
  the server.
- **LLMProvider.complete(system, user) -> str** — the only LLM contract (client side).
- **Audit line schema** — `{ts, event, ...fields}` JSON per line.
- **Report JSON** — sections 9.1 (internal) and 9.2 (bonus) of the assignment.

## 5. Deployment

- **Local:** `uv run copthief serve --role cop|thief` (HTTP on configured ports),
  orchestrator on the same host.
- **Cloud:** host the two MCP servers (e.g. Prefect Cloud / FastMCP host); expose via
  tokenized HTTPS URLs. LLM options: cloud API (recommended), or local Ollama exposed
  through an ngrok/Localtonet tunnel, or a fully-local hybrid (MCP in cloud, LLM local).

## 6. Risks

- LLM/network flakiness → gatekeeper retries + audit log.
- Firewalls blocking non-standard ports → documented; prefer outbound HTTPS.
- Strategy weakness → acceptable per assignment; Q-learning option provided.
