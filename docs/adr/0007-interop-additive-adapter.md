# ADR-0007: Inter-group bonus is an additive peer adapter, not a core change

- **Status:** Accepted

## Context
The §5.2 single-orchestrator core drives *both* agents and cannot drive an opaque opponent
owned by another team. The bonus requires two independent teams' agents to interoperate.

## Decision
Add a peer-to-peer adapter (`src/copthief/interop/`) alongside the core: free-text
`deliver_message`/`inbox` over MCP, commit-reveal capture verification, `SG:<index>`
framing, and byte-identical report digests — without modifying the §5.2 core.

## Consequences
- The graded self-game core stays untouched and spec-faithful.
- *Alternative rejected:* forcing the opponent to expose `move`/`observe` tools (breaks
  §5.1 free-language autonomy). See `docs/PRD_interop.md`.
