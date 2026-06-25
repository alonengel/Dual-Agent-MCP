# ADR-0009: Deterministic replay of the audit log

- **Status:** Accepted

## Context
The referee writes a per-turn audit log (ADR-0003). Nothing verified that a saved game is
actually reproducible from that log, so an engine regression could go unnoticed.

## Decision
Add `replay.py` (`replay_audit_log`): re-apply every logged turn to a fresh engine (the real
rules + subgame state machine), assert each reconstructed cell and each sub-game's outcome
match the record, and raise `ReplayError` on any divergence. Covered by unit tests
(synthetic divergence cases) and an integration test (a real self-game replays identically).

## Consequences
- Reproducibility is proven, not assumed; the log doubles as a regression fixture.
- A future "golden replay" suite can pin reference games as committed JSON.
