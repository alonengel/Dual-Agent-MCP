# Inter-Group Bonus — Shared Assumptions (CopThief)

Group **anrbj666** — Alon Engel, Renat Karimov · repo <https://github.com/alonengel/Dual-Agent-MCP>

To play the §12 inter-group bonus, **both teams must agree on the parameters below before the
match**. Mismatching rules — or final reports that don't match exactly — void the bonus for
that series (PDF §12.2). Defaults follow the assignment's config table (§10).

## 1. Board & movement (PDF §4.2–4.3)
- **Inter-group bonus board: 8×8** (re-frozen with group ImreEyal). The mandatory **self-game
  stays 5×5**; the §12 enhancement clause lets the two agents agree a larger board, and 8×8 moves
  capture into the *contested* zone so a strong thief can survive (5×5/25 made every sub-game a
  forced cop-win → a structural 75–75 tie). Scoring is unchanged (§12.2), so the grader schema is
  intact — only the board/round budget changes.
- Canonical frame **0-based, top-left, [row,col]**; our engine maps its own 1-based (x,y) via
  `to_cell`/`from_cell`. **No staying** — every ply steps to one of the **8** neighbours.
- Turn order: **thief moves first**, then cop, alternating. Capture = cop and thief share a cell
  (cop wins); thief surviving the round cap = thief wins. **Barriers off.**
- Start cells (8×8): **cop [0,0], thief [7,7]** (cop top-left, thief bottom-right — maximally
  apart). On 5×5 the same convention is [0,0]/[4,4].

## 2. Subgame & series (PDF §4.1, §12.1)
- **Negotiation path (with ImreEyal):** several freezes were tried before the final graded run:
  - **5×5 / 25 rounds** (Run 1, live) — every sub-game a cop-win → structural **75–75 tie**.
  - **8×8** with longer caps (**12**, **15**, and similar trials) — still too cop-heavy at both
    teams' strategy strength; most sub-games swept to the cop.
  - **8×8 / 7 rounds** (Run 2, live, shared seed) — first decisive series (**ImreEyal 80 /
    anrbj666 60**); byte-identical report emailed.
  §12.2 scoring never changed — only board size and round budget.
- **Frozen parameters:** subgame cap **7 rounds** on **8×8**; the graded **self-game** stays **25**
  on **5×5**.
- Series: **6 subgames** with role swap — subgames **0–2**: Group A (`group_1`) cop vs Group B
  (`group_2`) thief; subgames **3–5**: Group B cop vs Group A thief. We are `group_2` → thief 0–2,
  cop 3–5.

## 3. Barriers (PDF §4.3)
- Cop may place **≤ 5 barriers per subgame** on its own cell (impassable for both; costs the
  move). Thief cannot place barriers.

## 4. Scoring (PDF §4.4, Table 1)
| Outcome | Cop | Thief |
|---------|-----|-------|
| Cop wins | 20 | 5 |
| Thief wins | 5 | 10 |

## 5. Communication (PDF §5.1)
- **Free natural language** over MCP — no rigid protocol, no mandatory coordinate format.
- Messages convey intent / local observations / **deception**; a tolerant parser reads a
  coordinate only when one is volunteered.

## 6. Partial observation — agree explicitly (our DecPOMDP extension)
- `vision_radius` is **not** in the PDF config table, so both teams must agree if used:
  - **Option A (simplest):** full disclosure — `disclosure: exact` (deterministic series).
  - **Option B (hidden info):** shared `vision_radius: 1`, `disclosure: partial`.
- Deception (§5.1) is allowed; each side may enable it for its own thief.

## 7. Transport & security (PDF §6)
- MCP over **HTTPS**; each agent server requires a **bearer token** (`Authorization: Bearer …`).
- Each team shares: its **2 MCP URLs** (cop, thief) + its **bearer token**.
- Our endpoints: cop `https://mcp.alon.website/cop/mcp` · thief `https://mcp.alon.website/thief/mcp`.
- Either team may run the orchestrator (our `copthief netplay` against all four URLs); both
  teams independently verify the audit trail.

## 8. Reporting (PDF §9.2 / §12.2)
- After the series, **both** teams email the **identical** bonus JSON
  (`report_type: "bonus_game"`, `mutual_agreement: true`) to `rmisegal+uoh26b@gmail.com`.
- Any mismatch between the two reports → **0 points** for both teams, that series.

## 9. Pre-match checklist
1. Agree every parameter above (esp. §6 vision/disclosure and deception on/off).
2. Exchange the 4 MCP URLs + 2 bearer tokens.
3. Smoke-test connectivity (one `reset`/`observe` call each way).
4. Run the 6-subgame series with the role swap.
5. Reconcile the result; both teams email the matching bonus JSON.
