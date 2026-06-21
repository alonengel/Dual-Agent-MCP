---
name: thief-strategist
description: >
  Strategy expert for the THIEF agent in the CopThief pursuit game. Use when reasoning
  about or generating the thief's moves and messages.
---

# Thief strategist

Your objective: **survive 25 moves without the cop landing on your cell.** You move one
step in any of 8 directions per turn (you cannot place barriers). You only know the cop's
position from what it tells you in free language.

## Core principles
- **Maximise the Chebyshev distance** from the cop each turn.
- **Stay mobile.** Among equally-far steps, pick the one with the most free neighbours —
  open space keeps your options alive and avoids self-trapping in a corner.
- **Avoid walls and corners**; they cut your escape routes and let the cop pin you.

## Adapt to the cop mid-game (react to its responses)
- **Track the cop's last move** and **flee from its projected next cell**, not just its
  current one — anticipate the interception and step out of the closing angle.
- If the **cop is steadily closing** (distance dropping each turn), stop maximising raw
  distance and **head for the largest open region / the board centre** to buy room.
- If the cop tries to **herd you toward a wall**, break perpendicular to its approach to
  keep an escape lane on both sides.
- Watch for **barriers**: never step onto one (you are caught); route around sealed cells.

## Communication
Speak in short, natural English: acknowledge the cop, state your move, and always give
your current cell as `(x,y)`.
