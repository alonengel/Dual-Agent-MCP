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
   `127.0.0.1:11434` with **ngrok** (Traffic Policy + Basic Auth) or **Localtonet**.
   Point `OLLAMA_BASE_URL` at the tunnel URL; the MCP server reaches it with an auth
   header.
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
- **Tunnel a locally-running server (quickest).** Start a server locally and expose it:

```bash
# terminal 1 + 2: start the servers locally
uv run copthief serve --role cop
uv run copthief serve --role thief
# terminal 3 + 4: expose each port publicly (example with ngrok)
ngrok http 8181
ngrok http 8182
```

Then set `mcp.cop_url` / `mcp.thief_url` to the `https://...ngrok... /mcp` URLs.

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
preferred over username/password).

1. In the Google Cloud Console, create a project and enable the **Gmail API**.
2. Create **OAuth client credentials** (Desktop app); download `client_secret.json`
   into the project root (git-ignored). Optionally use a dedicated Gmail account.
3. First run opens a browser consent screen and writes `token.json` (also git-ignored).
4. Send:

```bash
uv run copthief selfplay --email      # or wire netplay to email similarly
```

If credentials are missing the emailer logs a warning and the report is still saved
to `results/` — it never crashes the run.

---

## 4. Inter-group bonus (Level 3) — one-week, no extensions

1. **Find a partner team** (coordinate over WhatsApp); agree on shared assumptions.
2. **Exchange** the four MCP URLs (cop+thief per team) and the tokens, out of band.
3. **Optional rule enhancements** — only in inter-group play, agreed at the *agent*
   level (e.g. 7 barriers, cop moves two steps, extra cops). Never contradict the base
   rules or the cop-win = 20 invariant. Express changes in `config.yaml` (no code edits)
   so both sides run the same parameters.
4. **Play 6 subgames**: 3 with your cop vs. their thief, 3 with your thief vs. their cop
   (see report section 9.2 / `build_bonus_report`).
5. **Both teams email matching reports.** The grader compares by group name; any
   mismatch or disagreement → 0 points for that series. Keep the **audit logs** — they
   are the only accepted evidence in a dispute.

### Scoring recap
- Per subgame: cop win 20/5, thief win 10/5 (max 90, min 30 per team).
- Bonus: higher total → 10, lower → 7, exact tie → 5 (averaged across series).

---

## 5. Security checklist before going public

- [ ] `COPTHIEF_MCP_TOKEN` set to a strong value; rotate/revoke when done.
- [ ] No secrets committed (`.env`, `client_secret.json`, `token.json` are git-ignored).
- [ ] MCP URLs reachable over HTTPS; non-standard inbound ports avoided where possible.
- [ ] LLM keys only in environment variables, never in source or config.
