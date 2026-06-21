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

- **ADR-1: SDK facade.** All logic flows through `CopThiefSDK`; GUI/CLI/tests never
  import internals directly. *Trade-off:* slight indirection for clean boundaries.
- **ADR-2: LLM lives only in the MCP client (orchestrator), per PDF section 5.2.**
  The two MCP servers expose pure tools (`reset`/`observe`/`move`/`place_barrier`/`note`)
  with no LLM and no strategy; the client runs both agent personas (each with its own
  LLM context, honouring the lecture's "each agent has an LLM"), decides + verbalises,
  and calls the tools to execute. *Trade-off:* the client is "heavier", but it exactly
  matches the formal spec and keeps servers trivially deployable/stateless-ish.
- **ADR-3: Referee holds authoritative state.** Agents keep only *beliefs* (DecPOMDP);
  the orchestrator validates every action, preventing illegal-move disputes.
- **ADR-4: HTTP transport even locally.** Prepares for cloud; avoids a stdio→HTTP
  rewrite later. *Alternative rejected:* stdio for local, HTTP for cloud.
- **ADR-5: Mock provider is a first-class provider**, not a test stub — it produces
  and parses the same free text as real providers, keeping CI meaningful and offline.
- **ADR-6: Config-driven everything.** No game parameter is hardcoded; values live in
  `config/*.yaml|json`, versioned and validated at startup.

## 4. Interfaces / Contracts

- **MCP tools (pure, per agent server):** `reset(x,y,barriers_left)`, `observe()`,
  `move(dx,dy)`, `place_barrier()`, `note(message)` — no LLM inside the server.
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
