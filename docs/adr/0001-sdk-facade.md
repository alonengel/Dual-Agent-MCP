# ADR-0001: Single SDK facade as the only entry point

- **Status:** Accepted

## Context
GUI, CLI, scripts and tests all need to run games and produce reports. Letting each
caller wire up internal modules (config, agents, match runner, reporting) would scatter
construction logic and couple consumers to internals.

## Decision
All logic flows through `CopThiefSDK` (`src/copthief/sdk/sdk.py`). External consumers call
the facade and never import internal modules directly (enforced by the layering in §4 of
the guidelines).

## Consequences
- Clean boundary; internals can be refactored without touching consumers.
- One obvious place to assemble components from config.
- Trade-off: a thin layer of indirection between callers and the domain.
