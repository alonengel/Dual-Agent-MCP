# Architecture Decision Records

One file per decision (format: Status / Context / Decision / Consequences). New decisions
get the next number and never rewrite history — a superseding ADR links back to the old one.

| ADR | Decision |
|-----|----------|
| [0001](0001-sdk-facade.md) | Single SDK facade as the only entry point |
| [0002](0002-llm-in-mcp-client.md) | The LLM lives only in the MCP client (orchestrator) |
| [0003](0003-referee-authoritative-state.md) | The referee holds authoritative state |
| [0004](0004-http-transport-local.md) | HTTP transport even for local play |
| [0005](0005-mock-provider-first-class.md) | The mock LLM provider is first-class |
| [0006](0006-config-driven.md) | Config-driven everything (no hardcoded parameters) |
| [0007](0007-interop-additive-adapter.md) | Inter-group bonus is an additive peer adapter |
| [0008](0008-probabilistic-belief-grid.md) | Probabilistic belief grid for partial observation |
| [0009](0009-deterministic-replay.md) | Deterministic replay of the audit log |
