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
coverage-optimal observation posts** whose vision windows tile the whole board (so there is
no blind spot; on boards too large to sweep within the move budget it falls back to the
corners — see `orchestrator/patrol.py`) — and switches to direct pursuit on re-acquisition;
the thief exploits being unseen to break contact toward open space (and may deceive).

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

- **State `s`:** the clipped relative offset of the opponent (`dx,dy ∈ [-3,3]`) **×** which
  3×3 board region the opponent occupies — a compact but board-aware 49×9 = 441-state table.
  The region lets the policy learn to corner against walls; an offset-only state converges to
  ≈ the heuristic, and a full per-neighbour blocked mask was too sparse (see REPORT §9.1).
- **Action `a`:** one of 8 step directions.
- **Reward `r`:** distance-shaped — the cop is rewarded for closing in, the thief for
  fleeing; capture yields ±10 (`shaped_reward`).
- **Policy:** ε-greedy exploration/exploitation, biased toward legal cells.
- **Trained** vs a fixed heuristic by `scripts/train_qtable.py`: ~0.40 cop win-rate (best
  ~0.57), past the 0.36 heuristic but short of the 0.66 lookahead minimax (REPORT §9.1).
- **Hyperparameters (config):** `learning_rate=0.1`, `discount_factor=0.9`,
  `epsilon=0.1` — all read from `config/config.yaml`, never hardcoded.

## 3a. Strategy B′ — Linear function approximation (RL, strongest learned cop)

`strategy/linear_q.py` replaces the table with a **linear value over afterstate features**:
the value of moving to a cell is `w · φ`, where `φ` = (distance to rival, rival escape cells,
own mobility, rival wall-clearance, capture/adjacency flags, and the **post-reply distance** —
the depth-1 lookahead signal). Weights are learned by **Monte-Carlo** return (bootstrapped TD
diverges here — the "deadly triad"). Because the features generalise across all positions, the
policy learns to weight cornering/capture *better than the hand-tuned minimax*: trained vs a
fixed heuristic it reaches **~0.80** cop win-rate, **beating the 0.66 lookahead** across thief
types (REPORT §9.1). Train with `scripts/train_qtable.py --policy linear`.

## 3b. Strategy C — Adaptive: anticipation + mid-game reaction

This strategy **adapts to the enemy's responses mid-game**. From the opponent's
last observed cell it computes a movement direction and **projects the opponent's next
cell**, then aims at that prediction (reusing the heuristic's cornering/mobility
tie-breaks and need-based barriers):

- **Cop — interception:** chase where the thief is *heading*, cutting the angle instead
  of trailing directly; still captures the real thief if it is actually adjacent.
- **Thief — evasion:** flee from where the cop is *heading*, stepping out of the closing
  angle rather than only away from the cop's current cell.
- Belief history resets at each subgame start (`move_number == 0`); predictions are
  clamped to the board.

## 3c. Strategy D — Lookahead (default): depth-1 minimax

The default strategy scores every legal step by the distance that remains **after the
opponent's best one-step reply**, rather than by the current distance:

- **Cop — interception:** minimise distance to the thief *after it flees*; this both
  intercepts better than greedy chasing and exploits walls/barriers that cap how far the
  thief can escape.
- **Thief — evasion:** maximise distance from the cop *after it gives chase*, with
  mobility/clearance tie-breaks; this favours pockets the cop cannot close on (behind a
  barrier or board edge). The cop's own cell is excluded so the thief never self-captures
  (the post-chase score is non-monotonic at distance 0 — see REPORT §13.1).

**Why it is the default:** [`scripts/strategy_arena.py`](../scripts/strategy_arena.py)
plays every policy pairing head-to-head (no LLM, perfect info). Among the **depth-1** policies
the lookahead **cop wins in every column** and `adaptive` is the weakest (especially as a
thief); the deeper minimax (§3d) is stronger still but lookahead is kept default for speed and
to keep self-play games long enough to be worth watching. It uses only legal moves and the
standard capture rule, so the game rules (PDF §4) are untouched.

## 3d. Strategy E — Minimax (depth-N): the strongest policy

`strategy/minimax.py` generalises the depth-1 lookahead to a full game-tree search. One
cop-perspective value drives both roles (cop **maximises** it → seek capture; thief
**minimises** it → run out the clock), with capture/timeout terminals mirroring the engine
clock, a Chebyshev-distance leaf at the horizon, and a per-decide transposition table (the
5×5 search is sub-millisecond per move). Win-rate climbs with depth until the game is solved:
at **depth ≥ 6 the cop captures from every 5×5 / 4-round start (1.00 vs every thief)** — the
~0.80 RL plateau was a *depth* limit of the one-ply policies, not the game (REPORT §9.1).
Two complementary results: at equal depth-1, *learning beats hand-tuning* (linear FA 0.79 vs
lookahead 0.65); lifting the depth cap *solves it*. Opt in via `strategy.kind: minimax`.

**Minimax does *not* improve the thief (negative result):** against the sub-optimal cops it
actually faces, the minimax thief is *worse* than the lookahead thief — minimax optimises vs a
*worst-case* cop, so it plays over-pessimistically and fails to exploit a myopic one. It only
edges ahead against a perfect cop, and a richer evasion leaf adds nothing (REPORT §9.1). So
`lookahead` stays the thief; *minimax ≠ best response to a weak opponent*.

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
- **Alternatives considered → adopted:** depth-N **minimax** (§3d) was added and *solves* the
  5×5 game; expectimax is unnecessary (the engine is deterministic). Deep RL stays out of scope
  (no GPU/time budget); linear function approximation (§3a) is the learned-policy sweet spot.
- **Success criteria:** strategies always emit a *legal-intent* move; the cop reliably
  captures on small boards; Q-update runs without error and is unit-tested.

## 6. Test Scenarios

- Cop closes distance / steps onto adjacent thief; thief increases distance.
- No free neighbours → `STAY`. Q-table `decide` + `learn` run; reward signs correct.
