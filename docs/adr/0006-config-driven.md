# ADR-0006: Config-driven everything (no hardcoded game parameters)

- **Status:** Accepted

## Context
The guidelines (§10) forbid hardcoded values. Grid size, move/round caps, scoring,
vision radius, MCP URLs and the report recipient must be tunable without code edits.

## Decision
All tunables live in versioned config (`config/config.yaml`, `rate_limits.json`,
`logging_config.json`), read through `Config` with dotted-key lookups and validated at
startup. The config version is asserted on load.

## Consequences
- Sanity-ladder board resizing, scoring tweaks and deploy URLs are config changes only.
- The version check fails loud on a stale/mismatched config.
