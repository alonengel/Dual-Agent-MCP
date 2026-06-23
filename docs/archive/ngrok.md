# ngrok tunnel setup (archived)

> **Status:** tested on Windows, June 2026. Kept for reference and for **ngrok paid**
> or **Ollama tunneling** (see DEPLOYMENT §1). For CopThief MCP public play we
> recommend **Cloudflare quick tunnel** instead — free ngrok stalled mid-match in
> our tests (see [Findings](#findings-free-tier) below).

---

## When ngrok still makes sense

- **ngrok paid** — removes free-tier connection limits; our code works as-is.
- **Ollama over a tunnel** — expose `127.0.0.1:11434` with Traffic Policy + Basic Auth
  (lecture approach); set `OLLAMA_BASE_URL` to the tunnel URL.
- **Historical reference** — documents the exact gotchas we hit so you do not repeat them.

For MCP servers, always use **`serve-combined`** (one port, path-routed) — never two
separate ngrok tunnels on the free tier.

---

## Prerequisites

```bash
uv run copthief serve-combined   # /cop/mcp and /thief/mcp on :8080
```

---

## Step-by-step (Windows)

1. **Install:** `winget install ngrok.ngrok` (or `choco install ngrok`).
2. **Auth:** create a free account → copy the authtoken →
   `ngrok config add-authtoken <token>`. The token is stored globally; it need not
   live in the project file.
3. **Update the agent (gotcha):** winget shipped an old agent (3.3.1). ngrok now
   requires **≥ 3.20.0** and rejects older ones with `ERR_NGROK_121`. Fix:
   `ngrok update` (we ended on 3.39.8).
4. **Config schema (gotcha):** this agent uses the **v2** YAML schema. A
   `version: "3"` file fails with `unknown version '3'`. Use
   [`ngrok.yml.example`](ngrok.yml.example) as a template.
5. **One domain on free (gotcha):** the free tier gives a **single assigned dev
   domain**. Defining two `http` tunnels made **both print the same URL** and ngrok
   pooled/round-robined them — cop requests randomly hit the thief server. Fix:
   one tunnel → `serve-combined` → `/cop/mcp` + `/thief/mcp`.
6. **Start:** `ngrok start --all --config ngrok.yml` → note the
   `https://<id>.ngrok-free.dev` URL (also at local inspector `http://127.0.0.1:4040`).
7. **Point the client:**
   ```yaml
   mcp:
     cop_url: "https://<id>.ngrok-free.dev/cop/mcp"
     thief_url: "https://<id>.ngrok-free.dev/thief/mcp"
   ```
   Set the same `COPTHIEF_MCP_TOKEN` on both ends, then `uv run copthief netplay`.

`ngrok.yml` in the project root is **git-ignored** (may hold your authtoken) — never
commit it. Use the example file in this folder instead.

---

## Findings (free tier)

The orchestrator reuses **one persistent MCP connection per server** and reconnects
once if a connection is dropped, so it makes very few connections. Verified
end-to-end over **localhost** (full 6-subgame match).

The **ngrok free tier**, however, proved **unreliable for a full public match**:

| Behaviour | Effect |
|-----------|--------|
| **New-connection rate cap** (~20/min) | A tight 60-call loop on one persistent connection passed; per-call reconnects failed at ~18. |
| **Idle connections dropped** | Between match phases the tunnel drops the link; re-establishing hangs ~30s and is refused. |
| **Browser interstitial** | Not the blocker — the client sends `ngrok-skip-browser-warning`. |

**Net result:** `netplay` over free ngrok stalled on the first post-negotiation call.

---

## Alternatives that worked

| Option | Notes |
|--------|-------|
| **Cloudflare quick tunnel** | Free, no account, full 6-subgame match verified — see [`../DEPLOYMENT.md`](../DEPLOYMENT.md). |
| **ngrok paid** | Removes connection limits. |
| **Free VM + Caddy** | e.g. Oracle Always Free running `serve-combined` behind HTTPS. |
