# ADR-0005: The mock LLM provider is first-class, not a test stub

- **Status:** Accepted

## Context
CI must run keyless and offline, yet the agents' behaviour depends on natural-language
generation and parsing. A throwaway test stub would diverge from real provider behaviour.

## Decision
`MockProvider` is a real provider: it produces and parses the *same* free text as the
cloud/Ollama providers (positions, taunts, claims), selected via `COPTHIEF_LLM_PROVIDER`.
It is the offline default and what `conftest.py` forces in tests.

## Consequences
- CI exercises the genuine dialogue/parse path with no API keys or cost.
- The same code path runs locally and in CI; only the provider swaps.
