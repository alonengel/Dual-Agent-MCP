# PRD — Decision-Making Strategy (Algorithm-Specific)

## 1. Background

The pursuit game is a **DecPOMDP** (decentralized, partially observable Markov
decision process): each agent observes only its own cell and what the rival *says*.
The assignment stresses that strategy is **secondary** to the pipeline, so the
default is a transparent heuristic, with an optional tabular Q-learning mechanism for
teams pursuing the competitive bonus.

Formal model: `⟨ n, S, {Aᵢ}, P, R, {Ωᵢ}, O, γ ⟩` where `n=2`, `S` = positions +
barriers, `Aᵢ` = move/block, `R` = the scoring table, `Ωᵢ/O` = partial observation.

**Partial observation matters to strategy:** an agent only sees the opponent's exact cell
within `vision_radius`; otherwise it acts on a (possibly stale) belief. The cop therefore
**hunts** when it loses the trail — it heads to the thief's *last-seen* cell, then **sweeps
the board corners** to flush it out — and switches to direct pursuit on re-acquisition; the
thief exploits being unseen to break contact toward open space (and may deceive).

**Negotiating the rules to your advantage (inter-group only):** since the vision radius
strongly favours one side (a wide radius lets the cop re-acquire at will; a narrow one
forces it to search blind), each agent *advocates* the radius that helps its role — the **cop requests a wider radius**, the
**thief a narrower one**. Per the assignment, an enhancement only takes effect if **both
sides agree**; on conflict the base radius applies (so a savvy thief simply refuses a wider
radius). In the self-game this is disabled — the base rules are followed exactly.

## 2. Strategy A — Heuristic (default)

- **Cop:** move to the reachable neighbour minimizing **Chebyshev distance** to the
  believed thief cell; step directly onto the thief when adjacent (capture). Among
  equidistant steps, tie-break by **cornering** — prefer the cell that also removes a
  thief escape route, herding it toward the walls.
- **Thief:** move to the reachable neighbour **maximizing** Chebyshev distance from
  the believed cop cell; among equidistant cells, tie-break by **open space** (most free
  neighbours, then clearance from the walls) to avoid being cornered.
- **Inputs:** observation (own cell, move number, barriers left), believed opponent
  cell (parsed from dialogue; exact in self-play). **Output:** a one-step `Move`.
- **Rationale:** deterministic, debuggable, zero-cost. The cornering tie-break plus the
  blind-search **hunt** make the cop a competent pursuer that reliably captures on small
  boards. As the board grows the thief's evasion holds, so the **cop-win rate falls with
  board size** (a sensitivity study — the actual game stays 5×5; see REPORT §9).
  **Limitation:** still one-step greedy with no multi-turn planning.

## 3. Strategy B — Tabular Q-learning (optional)

Implements the assignment's minimal Q-table with the Bellman update:

```
Q(s,a) ← Q(s,a) + α · [ r + γ · maxₐ′ Q(s′,a′) − Q(s,a) ]
```

- **State `s`:** the clipped relative offset of the opponent (`dx,dy ∈ [-3,3]`),
  giving a compact 49-state table per agent.
- **Action `a`:** one of 8 step directions.
- **Reward `r`:** distance-shaped — the cop is rewarded for closing in, the thief for
  fleeing; capture yields ±10 (`shaped_reward`).
- **Policy:** ε-greedy exploration/exploitation, biased toward legal cells.
- **Hyperparameters (config):** `learning_rate=0.1`, `discount_factor=0.9`,
  `epsilon=0.1` — all read from `config/config.yaml`, never hardcoded.

## 3b. Strategy C — Adaptive (default): anticipation + mid-game reaction

The default strategy **adapts to the enemy's responses mid-game**. From the opponent's
last observed cell it computes a movement direction and **projects the opponent's next
cell**, then aims at that prediction (reusing the heuristic's cornering/mobility
tie-breaks and need-based barriers):

- **Cop — interception:** chase where the thief is *heading*, cutting the angle instead
  of trailing directly; still captures the real thief if it is actually adjacent.
- **Thief — evasion:** flee from where the cop is *heading*, stepping out of the closing
  angle rather than only away from the cop's current cell.
- Belief history resets at each subgame start (`move_number == 0`); predictions are
  clamped to the board.

Two **strategy-expert skills** (`.claude/skills/cop-strategist`,
`.claude/skills/thief-strategist`) document the strategic principles and adaptation cues
(intercept the projection, herd toward walls, break perpendicular when herded, use
barriers only in a stand-off) for the LLM personas / Claude-Code development.

## 4. Inputs / Outputs / Performance

| Aspect | Heuristic | Q-table |
|--------|-----------|---------|
| Input | obs + belief | obs + belief |
| Output | one-step `Move` | one-step `Move` |
| Cost | O(neighbours) | O(actions) + table update |
| Training | none | online, per move |

## 5. Constraints, Alternatives, Success Criteria

- **Constraints:** one step/turn; barriers cop-only (≤5); moves validated by referee.
- **Alternatives considered:** minimax/expectimax (heavier, unnecessary for the
  pipeline goal); deep RL (out of scope — no GPU/time budget). Tabular Q-learning was
  chosen as the assignment-recommended, lightweight learning option.
- **Success criteria:** strategies always emit a *legal-intent* move; the cop reliably
  captures on small boards; Q-update runs without error and is unit-tested.

## 6. Test Scenarios

- Cop closes distance / steps onto adjacent thief; thief increases distance.
- No free neighbours → `STAY`. Q-table `decide` + `learn` run; reward signs correct.
