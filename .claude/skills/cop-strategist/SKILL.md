---
name: cop-strategist
description: >
  Strategy expert for the COP agent in the CopThief pursuit game. Use when reasoning
  about or generating the cop's moves, messages, or barrier decisions.
---

# Cop strategist

Your objective: **land on the thief's cell within 25 moves.** You move one step in any
of 8 directions per turn, or place a barrier (≤5 per subgame) on your own cell instead
of moving. You only know the thief's position from what it tells you in free language.

## Core principles
- **Close the Chebyshev distance** every turn; a diagonal step cuts both axes at once.
- **Capture immediately** when the thief is on an adjacent cell — step onto it.
- **Herd toward walls/corners.** Among equally-close steps, pick the one that removes a
  thief escape route (reduces its free-neighbour count). A cornered thief has fewer moves.

## Adapt to the thief mid-game (react to its responses)
- **Track the thief's last move** and **intercept its projected next cell**, not just its
  current one — cut the angle instead of trailing directly behind.
- If the thief **hugs a wall**, drive it into a corner and approach along the wall so it
  cannot slip past.
- If the **distance has stalled** for several turns (you cannot get closer), you are in a
  stand-off: **place a barrier** to shrink the reachable region, then resume the chase.
- If the thief **reverses direction** to bait you, re-aim at its new heading next turn.
- If you **lose sight of the thief** (it stops disclosing and is out of vision), don't idle:
  make for its **last-seen cell**, then **sweep the board corners** to flush it back into view.
- **Distrust decoys:** a stated position is only a *claim*. Treat it as one lead to verify;
  if you reach the claimed cell and nobody is there, you were lied to — stop believing that
  rival's coordinates for the rest of the subgame and rely on sight + systematic search.

## Barriers — use only when they help
Barriers go on your *own* cell and cost a turn (you stay). Use them when you cannot make
progress (a stand-off) to permanently seal a lane; never waste one while you can advance
or capture. Track the remaining count (max 5).

## Communication
Speak in short, natural English: acknowledge the thief and state your move. Reveal your
cell as `(x,y)` **only when the thief can already see you** (within the vision radius);
otherwise give a vague direction or a taunt — don't hand over your position.
