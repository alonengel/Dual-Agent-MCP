# PRD — Inter-Group Peer Interop (Bonus, "best of all worlds")

## 1. Background

The mandatory self-game uses our **single-orchestrator** architecture (PDF §5.2): the LLM
lives in the MCP client; the servers expose pure tools; one referee knows both true cells, so
capture is trivial. That model is simplest and spec-faithful for the graded deliverable, but
it **cannot drive an opaque opponent** — for the §12 inter-group bonus, two mutually-distrusting
codebases must interoperate without a shared referee.

A partner team (Imree Cohen, Eyal Shtinmetz — `Imreec/mcp-cop-thief`) proposed a **peer-to-peer**
protocol: agents exchange only free text (`deliver_message`), each runs its own engine, and
captures are verified with **commit-reveal** + a per-move **common-state hash**. That is the
correct design for the adversarial case. This PRD takes the **best of all worlds**: keep our
clean §5.2 core untouched, and add a separate `interop` adapter that speaks their protocol.

## 2. Goals & non-goals

- **Goal:** let our agent play another team's opaque agent for the bonus, reusing our existing
  `Agent`/`Subgame`/`strategy`/`dialogue` — without weakening the mandatory self-game.
- **Goal:** make terminal results **mutually verifiable** under partial observation + deception.
- **Non-goal:** replace the core. The interop layer is additive (`src/copthief/interop/`).
- **Non-goal:** pre-agree the *game rules* (Basket B) — those are negotiated live by the agents.

## 3. What we adopt from the partner protocol (Basket A — locked infra)

| Item | Decision |
|------|----------|
| Cross-agent channel | `deliver_message(text)` — **free text only**, no structured move/state fields |
| Auth | transport-level **bearer token** (`Authorization: Bearer …`), rejected before any tool runs |
| Capture verification | **commit-reveal**: `commit = SHA-256(cell ‖ nonce)` each move; reveal `cell+nonce` at a capture-claim / game end |
| Per-move sync | **common-state hash** of `{barriers, turn, move_count}` (sorted-key JSON); mismatch → technical loss + re-run |
| Canonical frame (commitments only) | **0-based, top-left, `[row, col]`, row-major** — fixed regardless of the display origin/indexing the agents negotiate |
| Report | byte-identical `bonus_game` JSON (§9.2 field order, UTF-8, no trailing space); **two-phase SHA-256 confirm** before each side emails independently |
| Logs | append-only per-subgame audit trail (our existing audit log) |

## 4. What stays in the live agent conversation (Basket B — never pre-agreed)

Board **origin**, coordinate **indexing** (0 vs 1), **turn timing**, and any **rule enrichment**
(extra barriers, bigger board, vision radius, extra scoring) — surfaced only in the agents'
free-language dialogue, by mutual consent, never contradicting the fixed core (a cop win is
always 20; the thief is never made stationary).

## 5. Design — additive `interop/` package

- `interop/commitment.py` — `to_cell`, `new_nonce`, `commit`, `verify`, `state_hash`.
- `interop/canonical.py` — `canonical_bytes`, `digest`, `reports_agree` (the two-phase confirm).
- `interop/peer.py` — `PeerMatch`: drives **one** side via a `Transport` (free-text + the
  fields above), reusing `Agent`/`Subgame`/`strategy`. Each side keeps its own engine; capture
  is claimed on belief and **confirmed by reveal**, so a deceptive opponent cannot fake or deny it.
- `agents/session.py` — adds `deliver_message(text)` (the free-text channel; LLM stays client-side).

## 6. Why commit-reveal (and the lighter alternative)

Under partial observation a cop only *believes* where the thief is; a deceptive thief could
otherwise fake or deny a capture, so the two engines could disagree → reports mismatch → 0 for
both (§12.2). Commit-reveal binds each true cell without revealing it, making the result
**verifiable without trust**. **Lighter alternative to offer the partner:** if both sides run
with **deception off / true-position disclosure**, the engines stay in sync from the prose and
commit-reveal becomes optional — a simpler interop if both agree.

## 7. Open items to confirm with the partner

1. Exact `bonus_game` field order for byte-identical reports (exchange one sample + diff).
2. The canonical-frame orientation (which physical corner is `[0,0]`).
3. Move-budget reading — we both treat **25 = 25 rounds** (our engine already counts rounds).
4. Whether deception is on (commit-reveal required) or off (lighter path).

## 8. Success criteria

- Self-game pipeline unchanged and still green.
- `commitment`/`canonical` unit-tested; `PeerMatch` plays a full in-process series and both
  sides derive the **same** result + matching report digest.
- Files ≤150 lines; ruff clean; coverage ≥85%.
