# Inter-Group Bonus — Shared Assumptions (CopThief)

Group **anrbj666** — Alon Engel, Renat Karimov · repo <https://github.com/alonengel/Dual-Agent-MCP>

To play the §12 inter-group bonus, **both teams must agree on the parameters below before the
match**. Mismatching rules — or final reports that don't match exactly — void the bonus for
that series (PDF §12.2). Defaults follow the assignment's config table (§10).

## 1. Board & movement (PDF §4.2–4.3)
- Grid **5×5**, origin **1** (cells (1,1)…(5,5)).
- One step in any of **8 directions** (diagonals allowed) per turn, or STAY.
- Turn order: **thief moves first**, then cop, alternating.
- Capture = cop and thief share a cell (cop wins). Thief surviving the move cap = thief wins.

## 2. Subgame & series (PDF §4.1, §12.1)
- Subgame: max **25 moves**.
- Series: **6 subgames** with role swap — subgames **1–3**: Group A cop vs Group B thief;
  subgames **4–6**: Group B cop vs Group A thief.

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
