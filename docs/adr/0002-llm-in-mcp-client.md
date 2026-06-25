# ADR-0002: The LLM lives only in the MCP client (orchestrator)

- **Status:** Accepted

## Context
The assignment (PDF §5.2) places the model in the MCP *client*. The two MCP servers must
expose tools, not intelligence.

## Decision
The two MCP servers expose pure tools (`reset`/`observe`/`move`/`place_barrier`/`note`)
with no LLM and no strategy. The client runs both agent personas — each with its own LLM
context (honouring the lecture's "each agent has an LLM") — decides and verbalises, then
calls the tools to execute.

## Consequences
- Exactly matches the formal spec; servers stay trivial and easy to deploy.
- Trade-off: the client is "heavier" and owns the orchestration logic.
