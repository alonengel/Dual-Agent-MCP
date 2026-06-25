# Cost Analysis — CopThief

Measured and estimated running costs for the exercise (PDF/guidelines §10–§11). Every
external LLM call is metered in `shared/usage.py`; after each match the SDK writes
`results/usage_<timestamp>.json` (git-ignored) with per-model token counts and `est_usd`.

## Summary (what we actually paid)

| Component | Path | Marginal cost |
|-----------|------|---------------|
| **LLM (primary)** | Claude **CLI / Claude Code** subscription | **$0** — included in membership; this is how we ran self-play, demos, and the live inter-group bonus |
| **LLM (fallback)** | Anthropic **API key** — **Claude Opus 4.8** (`claude-opus-4-8`) | **≈ $0.15** for one full **6-subgame session** — measured during **live MCP inter-group testing** with group ImreEyal (and a few local dev runs) |
| **Email reports** | Gmail API (`gmail.modify` OAuth) | **$0** — within free quota for the small JSON payloads we send |
| **MCP hosting** | Cloudflare named tunnel + local `serve-combined` | **$0** on free tier |
| **CI / tests** | `mock` LLM provider | **$0** |

**Bottom line:** day-to-day development and the graded inter-group runs cost **nothing** on
the Claude subscription (CLI). The only out-of-pocket LLM spend was **≈ $0.15** on API-key
runs while debugging the live MCP series with the partner team (six sub-games per session).

## LLM paths

### Claude CLI / Claude Code (default — $0 marginal)

- Config: `COPTHIEF_LLM_PROVIDER=claude` with the CLI on `PATH` (no API key required).
- **Model:** **Claude Opus 4.8** via the CLI `opus` alias (see `llm/claude.py`).
- Used for: verbose self-play, filmstrip capture, live inter-group series against ImreEyal.
- The usage meter still records **API-equivalent** `est_usd` so we can report what the
  subscription saved; actual billing is **$0** while the membership is active.

### Anthropic API key (fallback — paid)

- **Model:** **Claude Opus 4.8** — same as the CLI path. The API fallback sends
  `claude-opus-4-8` (`llm/claude.py`); the CLI uses the `opus` alias (latest Opus). The
  usage meter prices both under the Opus 4.8 row (**$5 / $25** per 1M input/output tokens).
- Used when the CLI was unavailable or too slow — notably during **live MCP bonus testing**
  against group ImreEyal (`run_bonus_series.py` over partner `trycloudflare` URLs + our
  `mcp.alon.website` tunnel), plus occasional local smoke tests.
- Messages are one–two sentences per turn, so token volume stays small even on Opus 4.8.
- **Measured:** one complete 6-subgame inter-group session on **Opus 4.8 via API** ≈ **$0.15**
  total (the graded final run used **Opus via CLI** instead — $0 marginal; see
  `assets/evidence/intergroup_cloud_run.log`).
- Keep the API key **disabled in the Anthropic console** except during active testing
  (see `docs/TODO.md` submission checklist).

## Gmail

- OAuth desktop flow; `token.json` git-ignored.
- Sends one small JSON attachment per report (`selfplay --email`, bonus series `--send`).
- No charge observed; well inside Google's free Gmail API daily quota.

## How metering works

1. `LLMProvider.complete()` (Template Method in `llm/base.py`) runs through the
   **API gatekeeper** (rate limits from `config/rate_limits.json`).
2. After each completion, `UsageMeter.record(model, prompt, completion)` estimates
   tokens (~4 chars/token) and applies the price table in `shared/usage.py`.
3. `CopThiefSDK` persists `results/usage_<ts>.json` when any calls were made.

Price table keys (USD per 1M tokens, input/output): Opus 4.8 **5 / 25**, Sonnet 4.6
**3 / 15**, etc. — see `_PRICING` in `usage.py`.

## Reproducing the numbers

```bash
# API path (will incur small API cost if key is enabled):
COPTHIEF_LLM_PROVIDER=claude uv run copthief selfplay --verbose
# then inspect results/usage_*.json

# Zero-cost path (CLI subscription):
# ensure claude CLI works, API key disabled in console
uv run copthief selfplay --verbose --gui --seed 3
```

For cost-sensitive runs, prefer the **CLI**; use the **API** only when the CLI is blocked
or for regression checks, then disable the key again.
