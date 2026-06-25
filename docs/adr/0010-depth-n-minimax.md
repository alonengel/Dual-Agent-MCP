# ADR-0010: Depth-N minimax search strategy

- **Status:** Accepted

## Context
The default `lookahead` strategy is a depth-1 minimax, and the strongest *learned* policy
(`linear_q.py`, RL) is a depth-1 afterstate value. Both plateaued around 0.65–0.80 cop
win-rate on the tight 5×5 / 4-round benchmark. A full game-tree search showed the plateau was
a **policy** limit, not a game limit: an optimal cop captures the lookahead thief from *every*
one of the 600 distinct starts — the benchmark is a forced cop win.

## Decision
Add `strategy/minimax.py` (`MinimaxStrategy`): a depth-capped minimax that generalises the
depth-1 lookahead. One cop-perspective value drives both roles — the cop maximises it (seek
capture), the thief minimises it (run out the move budget) — with capture/timeout terminals
mirroring the engine's turn order and clock, a Chebyshev-distance leaf at the horizon, and a
per-decide transposition table. Registered in the factory as `kind: minimax`; depth is config
(`strategy.minimax.depth`, default 8). Move-only: barriers are unnecessary once the search
forces capture.

## Consequences
- Depth-6 **solves** the benchmark (1.00 win-rate vs every thief, including an optimal minimax
  thief), at sub-millisecond cost per move on 5×5.
- Two honest, complementary results stand: at equal depth-1, *learning beats hand-tuning*
  (linear FA 0.79 vs lookahead 0.65); lifting the depth cap *solves the game*. The RL work is
  reframed as the strongest **fixed-horizon** cop, not the strongest cop outright.
- The default stays `lookahead` (fast, and its bounded horizon keeps self-play games
  non-trivial for the demo); `minimax` is the opt-in "strongest" policy. Regression-guarded by
  `tests/unit/test_minimax.py`.
