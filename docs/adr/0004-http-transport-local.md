# ADR-0004: HTTP transport even for local play

- **Status:** Accepted

## Context
MCP can run over stdio (simple, local) or HTTP (needed for cloud and inter-group play).
Using stdio locally and HTTP in the cloud would mean two transports and a later rewrite.

## Decision
Use HTTP transport everywhere, including local self-play. The local run binds to
`127.0.0.1`; cloud exposure adds a tunnel/PaaS in front of the same servers.

## Consequences
- One transport to test and reason about; the cloud step is configuration, not a rewrite.
- *Alternative rejected:* stdio locally + HTTP for cloud (two code paths).
