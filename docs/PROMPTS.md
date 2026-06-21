# Prompt-Engineering Log

This log documents the significant AI prompts used to build CopThief, the context
and intent behind each, and the iterative refinements — as required by the
professional-software guidelines (section 8.3, "Prompt Book").

## 1. Requirements synthesis

- **Context:** three source documents — the Exercise-6 PDF, a lecture transcript,
  and a gap analysis comparing them.
- **Prompt intent:** "Read all three sources and merge them into a single set of
  requirements, surfacing requirements that appear only in the lecture."
- **Outcome:** identified five lecture-only requirements (critical audit logging,
  HTTP-even-locally, agent-level rule enhancement, deadline structure, per-agent
  email). These were promoted to first-class requirements in the PRD.
- **Refinement:** explicitly re-prioritised "working pipeline > strategy" after the
  transcript repeatedly stressed it.

## 2. Architecture design

- **Prompt intent:** "Design an SDK-layered architecture with ≤150-line files that
  reconciles 'LLM in the MCP client' (PDF) with 'each agent needs an LLM' (lecture)."
- **Outcome:** ADR-2 — orchestrator owns dialogue logic; each agent session owns its
  own provider for verbalisation. Referee holds authoritative state (ADR-3).
- **Refinement:** split the orchestrator into in-process self-play and a networked
  MCP client so the same domain code serves both local and cloud topologies.

## 3. Domain engine

- **Prompt intent:** "Implement a turn-based pursuit subgame state machine: thief
  first, 8-direction moves, cop barriers (max 5), capture/survival outcomes."
- **Refinement:** separated `rules.validate()` (pure legality) from `Subgame.apply()`
  (state mutation) for testability; move counter advances only after the cop plays.

## 4. Natural-language dialogue

- **Prompt intent:** "Agents must talk in free text, not a rigid protocol. Make the
  LLM verbalise a move and parse the rival's sentence into a coordinate."
- **Iteration:** first version embedded the move delta as `(dx,dy)`, which the
  coordinate parser mistakenly grabbed before the position. Fixed by rephrasing the
  delta as `dx= dy=` so the only `(x,y)` token is the cell. (Captured as a test.)

## 5. Offline-first LLM strategy

- **Prompt intent:** "Make the pipeline runnable and CI-testable without a live LLM,
  while keeping the test meaningful."
- **Outcome:** the `MockProvider` produces and the dialogue layer parses the same
  free text as real providers — a first-class provider, not a bypass stub (ADR-5).

## 6. Testing & quality gates

- **Prompt intent:** "Write unit + integration tests mirroring `src/`, mock external
  HTTP/LLM, reach ≥85% coverage; keep every file ≤150 lines and ruff-clean."
- **Outcome:** 67 tests, ~97% coverage; HTTP providers tested via monkeypatched
  transport; the networked client driven by a mocked `NetworkMatch` in the SDK test.
