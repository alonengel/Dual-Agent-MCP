# Deployment Guide

This guide covers the three exercise levels. **Level 1 (local self-game)** already
works out of the box (`uv run copthief selfplay`). This document focuses on
**Level 2 (cloud self-game)** and **Level 3 (inter-group bonus)**.

> Each team needs **two** public MCP URLs — one for the cop server, one for the
> thief server — and every URL must be protected by a **token** that can be revoked.

---

## 0. Prerequisites

```bash
uv sync
cp .env.example .env      # then edit values below
```

Set in `.env` (or the shell environment):

| Variable | Purpose |
|----------|---------|
| `COPTHIEF_MCP_TOKEN` | shared secret guarding every MCP tool call (revoke to cut access) |
| `COPTHIEF_LLM_PROVIDER` | `mock` \| `ollama` \| `api` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | cloud LLM (if `api`) |
| `OLLAMA_BASE_URL` | local Ollama endpoint (if `ollama`) |
| `GMAIL_CLIENT_SECRET_FILE` / `GMAIL_TOKEN_FILE` | Gmail OAuth files |

---

## 1. LLM architecture — choose one

Even in the cloud the MCP server still needs an LLM. The lecture describes three
approaches; configure via `config.yaml` `llm.provider` (+ `.env`).

1. **Cloud API key (recommended, simplest).** Set `llm.provider: api` and the
   matching `*_API_KEY`. No local machine exposure; cheap because messages are short.
2. **Local Ollama exposed via a secure tunnel.** Run Ollama locally, then expose
   `127.0.0.1:11434` with a tunnel (ngrok paid, Localtonet, etc.). See
   [`docs/archive/ngrok.md`](archive/ngrok.md) for ngrok notes. Point `OLLAMA_BASE_URL`
   at the tunnel URL; the MCP server reaches it with an auth header.
3. **Hybrid (safest local dev).** Keep the LLM **and** the game client on your
   machine; only the MCP servers are public. The client makes **outbound** HTTPS to
   the cloud servers — no inbound ports, no IP exposure.

---

## 2. Cloud hosting of the MCP servers (Level 2)

The two servers are plain FastMCP HTTP apps (`copthief serve --role cop|thief`).
Host them anywhere reachable from the public internet:

- **Managed MCP host (Prefect/FastMCP cloud).** Deploy each server; you receive a
  public HTTPS URL. Put those URLs in `config.yaml` under `mcp.cop_url` / `mcp.thief_url`.
- **Your own VM (e.g. free GCP credits).** Run both servers on different ports behind
  a reverse proxy with TLS; open only the needed ports.
- **Tunnel a locally-running server (quickest).** Use **single-endpoint mode** so one public
  URL covers both agents (required for free tunnels):

```bash
uv run copthief serve-combined   # /cop/mcp and /thief/mcp on :8080
# then expose :8080 with Cloudflare (recommended) or ngrok paid — see below
```

### Cloudflare quick tunnel (recommended — verified free)
Full 6-subgame `netplay` completed end-to-end over a `trycloudflare.com` quick tunnel:

```bash
winget install Cloudflare.cloudflared          # one-time
uv run copthief serve-combined                 # terminal 1 (:8080)
cloudflared tunnel --url http://localhost:8080 # terminal 2 -> prints https URL
```

Or one command: `powershell -File tasks.ps1 cloud`

Then set in `config/config.yaml`:
```yaml
mcp:
  cop_url: "https://<id>.trycloudflare.com/cop/mcp"
  thief_url: "https://<id>.trycloudflare.com/thief/mcp"
```
Keep the same `COPTHIEF_MCP_TOKEN` on both ends and run `uv run copthief netplay`.
Quick-tunnel URLs change each run; for a fixed URL use a free Cloudflare account +
named tunnel.

**Local two-server mode** (no tunnel) still works for development:
```bash
uv run copthief serve --role cop      # :8181
uv run copthief serve --role thief     # :8182
# or: powershell -File scripts/run_local_cloud.ps1
```

### Other tunnel options
- **ngrok (paid)** or **free VM + Caddy** — also work with `serve-combined`.
- **ngrok free tier** — tested but **unreliable** for a full match (connection-rate cap
  + idle drops). Full walkthrough, gotchas, and example config are archived in
  [`docs/archive/ngrok.md`](archive/ngrok.md) (not recommended for CopThief public play).

The orchestrator reuses persistent MCP connections and reconnects once on failure; the
client also sends `ngrok-skip-browser-warning` for ngrok hosts.

**Network cautions (from the lecture):** corporate firewalls may block non-standard
ports — prefer outbound HTTPS and test from a permissive network. Verify each URL is
publicly reachable and **token-protected** before sharing it.

### Verify the cloud pipeline
With both URLs configured and the token set on both ends:

```bash
uv run copthief netplay --seed 7   # orchestrator drives the remote servers
```

This is the same flow as the local proof (`scripts/run_local_cloud.ps1`), just with
public URLs instead of `127.0.0.1`.

---

## 3. Gmail API for the report email

The cop agent emails the JSON report at the end of 6 subgames (token-based OAuth,
preferred over username/password). This follows the course Gmail-API guide exactly:

1. In the **Google Cloud Console**, select/create one project for the whole flow.
2. **APIs & Services → Library**: enable the **Gmail API** (the guide also enables the
   Calendar API; only Gmail is required here).
3. **Google Auth Platform** (separate from API enablement):
   - **Audience** → choose **External** (enables Testing mode with a Test-users list).
   - **Audience → Test users** → add the Gmail address you will send from.
   - **Data access → Add scopes** → add `https://www.googleapis.com/auth/gmail.modify`.
4. **Clients → Create OAuth client → Application type: Desktop**. Download the JSON and
   save it as **`credentials.json`** in the project root (git-ignored).
5. First send opens a browser consent screen and writes **`token.json`** (git-ignored).
   This matches the emailer's defaults (`GMAIL_CLIENT_SECRET_FILE=credentials.json`,
   scope `gmail.modify`).
6. Send:

```bash
uv run copthief selfplay --email
```

If credentials are missing the emailer logs a warning and the report is still saved
to `results/` — it never crashes the run.

**Troubleshooting:** "Access blocked / app isn't verified" is normal in Testing mode as
long as your account is in Test users. If you changed scopes, delete `token.json` and
re-run to force a fresh consent.

---

## 4. Inter-group bonus (Level 3) — one-week, no extensions

### How the professor wants MCP to work between teams (PDF §5, §6, §12 + lecture)
- **Each team runs its own two MCP servers** — one for the **cop**, one for the **thief**
  — so a team publishes **two URLs**. Servers are FastMCP over HTTP(S), each guarded by a
  **token** that can be revoked.
- **Agents are autonomous and isolated**: an agent knows nothing about the rival except
  what it is told. They coordinate in **free natural language** (no rigid protocol); the
  internal implementation is irrelevant "as long as they understand each other"
  (lecture). Our design keeps the **LLM in the client/orchestrator** (PDF §5.2) and the
  servers as pure tools.
- **Pairing is arranged out-of-band first** (WhatsApp/phone): you agree to play, then
  **exchange tokens and URLs**. The token is the access control — delete/rotate it to cut
  the other side off.
- **Role split (PDF §12.1):** 6 subgames — 3 with **your cop vs. their thief**, then 3
  with **your thief vs. their cop**.
- **Autonomous result reporting:** at the end of the 6 subgames **each team emails its own
  JSON report** to the course address. The grader **compares the two reports by group
  name**; the bonus counts **only if both reports agree exactly** — any mismatch or
  disagreement → **0 for both** (lecture: "his agent auto-rejects"). Keep the **audit
  logs** as the only accepted dispute evidence.

### How you'll use it (Cloudflare — verified, free, no account)
```bash
winget install Cloudflare.cloudflared           # one-time (done)
uv run copthief serve-combined                  # terminal 1  (:8080, both agents)
cloudflared tunnel --url http://localhost:8080  # terminal 2  -> prints your https URL
```
Then share these with your partner team (and set the same `COPTHIEF_MCP_TOKEN` on both
ends):
```
https://<id>.trycloudflare.com/cop/mcp
https://<id>.trycloudflare.com/thief/mcp
```
Whoever runs the match sets the four URLs in `config.yaml` (`mcp.cop_url`/`thief_url` for
each side) and runs `uv run copthief netplay`. Quick-tunnel URLs change each run; use a
free Cloudflare account + named tunnel if you want a fixed URL.

### Steps
1. **Find a partner team** (coordinate over WhatsApp); agree on shared assumptions.
2. **Exchange** the MCP URLs (cop+thief per team) and the tokens, out of band.
3. **Optional rule enhancements** — only in inter-group play, agreed at the *agent*
   level (e.g. 7 barriers, wider vision radius). Never contradict the base rules or the
   cop-win = 20 invariant. Express changes in `config.yaml` (no code edits) so both sides
   run the same parameters.
4. **Play 6 subgames** (role split above; see report §9.2 / `build_bonus_report`).
5. **Both teams email matching reports** (`netplay --email`); mismatch → 0 for that series.

### Scoring recap
- Per subgame: cop win 20/5, thief win 10/5 (max 90, min 30 per team).
- Bonus: higher total → 10, lower → 7, exact tie → 5 (averaged across valid series).

---

## 5. Security checklist before going public

- [ ] `COPTHIEF_MCP_TOKEN` set to a strong value; the servers enforce it as a
      transport-level **bearer token** (`Authorization: Bearer <token>`), and the
      orchestrator sends it automatically. A wrong/absent token returns **401**.
      Rotate the token to revoke access instantly.
- [ ] No secrets committed (`.env`, `client_secret.json`, `token.json` are git-ignored).
- [ ] MCP URLs reachable over HTTPS; non-standard inbound ports avoided where possible.
- [ ] LLM keys only in environment variables, never in source or config.
