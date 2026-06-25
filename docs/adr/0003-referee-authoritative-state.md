# ADR-0003: The referee holds authoritative state

- **Status:** Accepted

## Context
In a partially-observable game each agent has its own (possibly wrong) view. If agents also
owned the ground-truth state, illegal-move and capture disputes would be unresolvable.

## Decision
The orchestrator is the single referee: it holds authoritative board state and validates
every action. Agents keep only *beliefs* (the Dec-POMDP observation), never ground truth.

## Consequences
- No illegal-move disputes; capture is decided in one place.
- The audit log written by the referee is the canonical record (see ADR-0004, ADR-0009).
