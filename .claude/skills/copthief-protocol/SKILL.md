---
name: copthief-protocol
description: >
  How the autonomous Cop and Thief agents talk over MCP and play the pursuit game.
  Use when generating or debugging the agents' free-language negotiation and moves.
---

# CopThief agent protocol

Two autonomous agents — **Cop** and **Thief** — each run as their own MCP server.
Per PDF section 5.2 the **LLM lives in the MCP client (orchestrator)**, not the servers:
the servers expose **pure tools** (`reset`, `observe`, `move`, `place_barrier`, `note`)
and the client runs each agent's LLM persona, decides, verbalises, and calls the tools.
There is **no rigid wire protocol** (PDF §5.1): agents coordinate in **free natural
language**, describing their **intentions, local observations, or attempts at deception** —
they do **not** pass raw numeric coordinates as a protocol. A message *may* reveal the
speaker's cell as `(x,y)` (a tolerant parser reads it if present), but only when that serves
the role; under partial observation a hidden agent withholds it.

## Roles & objective
- **Cop**: reach the thief's cell (capture). Pursuing, calm tone.
- **Thief**: survive the whole game (default 25 moves) without being caught. Evasive tone.

## Turn discipline
- Turn-based; the **thief moves first**, then the cop, alternating.
- One step per turn in any of the 8 directions (diagonals allowed). The cop may instead
  place a barrier on its current cell (max 5); the thief cannot place barriers.
- Capture = cop and thief share a cell. Entering a barrier is illegal.

## Message contract (free text, one or two sentences)
1. Acknowledge the opponent's last message.
2. Convey your move/intent in character ("I step up-right", "I hold and drop a barrier").
3. Reveal your cell as `(x,y)` **only when appropriate** — the cop may; a hidden thief
   instead gives a vague direction, states intent, or deceives (PDF §5.1).

## Negotiation / handshake (start of a subgame)
Agree, in natural language, on: board size and origin, turn order (thief first), and any
mutually-agreed rule enhancements (inter-group only; never contradict the base rules or
the fixed cop-win = 20 score).

## Hard invariants
- Never invent illegal moves; the orchestrator (referee) validates everything.
- Self-game (single team): follow the base rules exactly — no enhancements.
- When you *do* reveal a position, write it as `(x,y)` so the parser reads it; withholding
  it under partial observation is legitimate (the opponent's belief simply goes stale).
