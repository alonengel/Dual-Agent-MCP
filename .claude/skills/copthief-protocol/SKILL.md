---
name: copthief-protocol
description: >
  How the autonomous Cop and Thief agents talk over MCP and play the pursuit game.
  Use when generating or debugging the agents' free-language negotiation and moves.
---

# CopThief agent protocol

Two autonomous agents — **Cop** and **Thief** — each run as their own MCP server and
talk through a relay (the orchestrator). There is **no rigid wire protocol**: agents
coordinate in **free natural language**. A tolerant parser extracts coordinates, so
every message MUST state the speaker's current cell as `(x,y)`.

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
2. State your move ("I step up-right", "I hold and drop a barrier").
3. State your resulting position explicitly as `(x,y)`.

## Negotiation / handshake (start of a subgame)
Agree, in natural language, on: board size and origin, turn order (thief first), and any
mutually-agreed rule enhancements (inter-group only; never contradict the base rules or
the fixed cop-win = 20 score).

## Hard invariants
- Never invent illegal moves; the orchestrator (referee) validates everything.
- Self-game (single team): follow the base rules exactly — no enhancements.
- Always include a real `(x,y)`; ambiguous messages break the opponent's belief update.
