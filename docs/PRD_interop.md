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
| Loop model | **async / client-driven** (confirmed): on my turn my client decides + calls *their* `deliver_message` (ack only), then polls *my* inbox for their turn. Both LLMs client-side; servers only carry messages. |
| Game mode | **Option A — full disclosure + commit-reveal audit** (confirmed): each ply states the mover's new cell in cleartext, so both engines stay in lockstep and capture is deterministic. Partial-obs/deception is exercised in the graded self-game; the bonus = inter-group play working. |
| Cross-agent channel | `deliver_message(text)` — **free text only** (a dumb mailbox: records the text, returns an ack, never touches an LLM). The exact values ride along as one verbatim block the receiver extracts with a tolerant regex (`interop/wire.py`): `MOVE:[row,col] \| COMMIT:<sha256> \| NONCE:<nonce> \| STATE:<sha256>`. |
| Auth | transport-level **bearer token** (`Authorization: Bearer …`), rejected before any tool runs; each remote URL takes its own token (their cop/thief tokens, our one token) |
| Capture verification | **deterministic from cleartext** `MOVE` (cop cell == thief cell); the per-ply `COMMIT = SHA-256(canonical{nonce,pos:[row,col]})` + revealed `NONCE` are a tamper-evident **audit** (matched to partner test vector) |
| Per-move sync | **common-state hash** of `{barriers, move_count, turn}` (sorted-key compact JSON), computed *after* the mover's ply (`move_count`=plies done, `turn`=next mover); mismatch → void + re-run (matched to partner test vector) |
| Barriers | **disabled for the run** (`max_barriers=0`, confirmed) — weak on an open 5×5 and keeps `STATE.barriers` `[]` so the two engines stay trivially in sync |
| Canonical frame (commitments only) | **0-based, top-left, `[row, col]`, row-major** — confirmed; fixed regardless of the display origin/indexing the agents negotiate |
| Report | byte-identical `bonus_game` JSON (`sort_keys`, `separators=(",",":")`, no version key; sub-game = `{index, winner, cop_score, thief_score}`); **two-phase SHA-256 confirm** before each side emails independently |
| Logs | append-only per-subgame audit trail (our existing audit log) |

## 4. What stays in the live agent conversation (Basket B — never pre-agreed)

Board **origin**, coordinate **indexing** (0 vs 1), **turn timing**, and any **rule enrichment**
(extra barriers, bigger board, vision radius, extra scoring) — surfaced only in the agents'
free-language dialogue, by mutual consent, never contradicting the fixed core (a cop win is
always 20; the thief is never made stationary).

## 5. Design — additive `interop/` package

- `interop/commitment.py` — `to_cell`, `new_nonce`, `commit`, `verify`, `state_hash`.
- `interop/canonical.py` — `canonical_bytes`, `digest`, `reports_agree` (the two-phase confirm).
- `interop/wire.py` — `encode`/`decode`: embed/extract the agreed verbatim
  `MOVE:[row,col] | COMMIT:<sha256> | NONCE:<nonce> | STATE:<sha256>` block inside the free-text
  message (an LLM can't reliably copy 64-hex, so the block is parsed deterministically while the
  surrounding prose stays natural).
- `interop/peer.py` — envelope/frame helpers: `from_cell` (inverse of `to_cell`), `state_in_sync`,
  plus `make_envelope`/`confirm_capture` (used by the in-process reference for the hidden-thief
  variant we also support).
- `interop/transport.py` — the async §5.2 mailbox client: `deliver(url, token, text)` (call the
  opponent's `deliver_message`, ack only, with **retry-with-backoff** for the peer's transient
  5xx/connection drops), `read_inbox(url, token)` (read our own full `inbox()` mailbox), `live_io(...)`
  which builds the per-sub-game `(send, recv)`, and **`exchange_hash(...)`** — the automated
  two-phase confirm: deliver our report's `REPORT_SHA:<hex>` to the peer and poll our inbox for
  theirs. `inbox()` returns the *full* ordered message list (vs `observe()`'s last-5 snapshot), so
  no turn is dropped over a long subgame.
- `interop/peer_series.py` — `play_series` + `score_series`: drives the **6-sub-game role-swap
  series** (per §12.1 we are `group_2`, thief-first: `OUR_SCHEDULE`) over `PeerLoop` with injected
  I/O, then scores it into the byte-canonical match dict (0-based `sub_games` + `totals_by_group`)
  for `build_bonus_report`. Start cells are the agreed canonical `[0,0]`/`[4,4]`.
- `scripts/run_bonus_series.py` — the live driver: wires Claude agents + `live_io` → `play_series`
  → `score_series` → `build_bonus_report`, then runs the **automated two-phase confirm**
  (`transport.exchange_hash`) and **emails only on a hash match** (a mismatch or a no-hash timeout
  aborts without sending — the §12.2 path). Degrades to manual if the peer sends no `REPORT_SHA`.
- `interop/peer_loop.py` — **`PeerLoop`**: the live **async client-driven** turn loop (Option A).
  Drives our turns with our `Agent`/`strategy`, states our new cell in cleartext + appends the
  commit/nonce/state block, audits each incoming block (commit must open to the stated move; state
  must match) and adopts the cleartext move as belief. Capture is **deterministic** when the cells
  coincide; a failed audit raises `PeerDesyncError` (§12 void + re-run). `send`/`recv` are injected,
  so two loops wire in-process for tests without a network.
- `interop/peer_match.py` — `PeerMatch`: an in-process, refereeless reference that plays a full
  series with both engines in one process, settling capture by **commit-reveal handshake** (the
  hidden-thief / Option B variant) — proves that path composes even though the live run uses A.
- `agents/session.py` — `deliver_message(text)` (the dumb mailbox; LLM stays client-side).

## 6. Why we chose Option A (and still keep commit-reveal)

Both teams already exercise partial observation + deception in their **graded self-game**, so for
the bonus the goal is simply *inter-group play that works and agrees*. Option A (full disclosure)
makes that deterministic: each ply states the true cell, both engines stay in lockstep, and a
capture is decided identically on both sides — no trusted referee and no risk of the two engines
disagreeing on a hidden capture. Commit-reveal is **not dropped**: the per-ply `COMMIT`+`NONCE`
remain a tamper-evident audit, and the full hidden-thief handshake stays implemented and tested in
`PeerMatch` (Option B) in case a future partner wants it.

## 7. Status with the partner (group ImreEyal)

**Run 1 (5×5 / 25 rounds) — complete.** Full 6-sub-game series played live over the tunnels with
Claude on both sides; reports were byte-identical (matching SHA-256 `8aab1c0…`) and emailed. Result:
all six forced cop-wins → a structural **75–75 tie** (on 5×5/25 the cop always corners the thief, and
the role swap equalises totals).

**Run 2 (re-frozen to break the tie) — complete (24 Jun 2026).** Kept §12.2 scoring exactly and
changed only the game so a strong thief can survive:
- Board **8×8**, **7 rounds** (re-frozen from 12), shared seed, start **cop `[0,0]` / thief `[7,7]`**.
- Unchanged: async dumb-mailbox · Option A full disclosure · `MOVE|COMMIT|NONCE|STATE` block ·
  **STATE non-fatal** (redundant with barriers off; commit-verify + cleartext positions carry
  correctness, move_count drifts a step under retries) · barriers off · thief-first · 8-dir ·
  retry-safe + COMMIT-dedup both ways · 0-based `[row,col]` · `SG:<index>` framing ·
  `group_1=ImreEyal`/`group_2=anrbj666` · schedule group_1 cop 0–2 (we thief), group_2 cop 3–5 ·
  scoring 20/5 · 5/10.
- **Automated two-phase confirm** (`REPORT_SHA:<sha256>` over the channel) both sides; email only on
  a confirmed match. `commit`/`state_hash` pinned to their **test vectors** (regression-tested).
- Live over partner `trycloudflare` URLs + our `mcp.alon.website` named tunnel; byte-identical report
  SHA `c5ad6776…`, emailed after hash match. Result: **ImreEyal 80 / anrbj666 60** (bonus claim 10 vs 7).
  Evidence: `assets/evidence/intergroup_cloud_run.log`, `assets/evidence/bonus_game_report.json`.

## 8. Success criteria

- Self-game pipeline unchanged and still green.
- `commitment`/`canonical`/`wire` unit-tested; commit + state hashes match the partner vectors.
- `PeerLoop` plays a full **async** subgame (two loops over in-process queues), audits every block,
  and both sides derive the **same** deterministic result; a tampered block raises `PeerDesyncError`.
- `peer_series` plays the full **6-sub-game role-swap series** in-process and scores it into a
  byte-canonical match dict (0-based, per-group totals) the partner's builder reproduces.
- Files ≤150 lines; ruff clean; coverage ≥85% (currently ~96%).
