# ADR-0008: Probabilistic belief grid for partial observation

- **Status:** Accepted

## Context
The cop's earlier blind search used a single believed cell plus a fixed patrol. Under
Chebyshev vision radius 1 the rival is usually unseen, and a point belief discards the
distribution of where it might be — weak Dec-POMDP modelling.

## Decision
Add `belief/grid.py` (`BeliefGrid`): a normalised probability distribution over free cells,
updated by three Dec-POMDP channels — `diffuse` (physics: forced one-step move),
`observe_not_at` (hard negative info from commit-reveal / "no capture"), and `observe_claim`
(soft nudge from a fallible message). The new `belief` strategy runs the existing depth-1
minimax against the grid's most-likely cell — combining belief tracking with adversarial
lookahead (something neither policy has alone). A rival within `sight_radius` is treated as a
confirmed sighting and **collapses** the grid to that exact cell, so ground truth is never
diluted by the soft filter.

## Consequences
- Principled Dec-POMDP belief; the cop pursues the highest-probability region.
- Opt-in (`strategy.kind: belief`); `lookahead` stays the default until validated in play.
- With perfect information it tracks the truth and reduces to plain lookahead.
