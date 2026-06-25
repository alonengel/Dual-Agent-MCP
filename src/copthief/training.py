"""Reinforcement-learning trainer: tabular Q-learning vs a fixed heuristic opponent.

Each Q-learner trains against a *stationary* heuristic opponent of the other role (rather
than co-adapting self-play, which gives a moving target and a noisy curve): the cop learns
to capture a heuristic thief, the thief to evade a heuristic cop. Rewards are distance-shaped
(`shaped_reward`) with a terminal capture bonus/penalty; exploration anneals from `eps_start`
to `eps_end`. Every `eval_every` games the greedy cop is measured against the heuristic thief,
so the learning curve is directly comparable to what is being trained.

Games run on a deliberately tight clock (small board, few rounds) so the cop cannot win by
default — a better-learned policy captures more often. (Q-learning tops out near the greedy
ceiling here; an edge/barrier-aware state was tested and *regressed* it — see README §9.1.)
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from copthief.constants import Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.domain.subgame import Subgame
from copthief.strategy.base import Strategy, chebyshev
from copthief.strategy.factory import build_strategy
from copthief.strategy.qlearning import QTableStrategy, shaped_reward


@dataclass
class TrainConfig:
    """Hyper-parameters for a training run (all overridable from the CLI)."""

    games: int = 1000
    grid: int = 5
    rounds: int = 4          # tight clock: the cop must capture quickly, so skill shows
    max_barriers: int = 5
    learning_rate: float = 0.2
    discount: float = 0.9
    eps_start: float = 0.5
    eps_end: float = 0.02
    eval_every: int = 100
    eval_games: int = 200
    seed: int = 0


def _epsilon(step: int, total: int, start: float, end: float) -> float:
    """Linearly anneal exploration from ``start`` to ``end`` over the run."""
    return end if total <= 1 else start + (end - start) * (step / (total - 1))


def _start_cells(board: Board, rng: random.Random) -> tuple[Position, Position]:
    """Two distinct random free cells for the cop and the thief."""
    cop = board.random_free_cell(rng, exclude=set())
    thief = board.random_free_cell(rng, exclude={cop.as_tuple()})
    return cop, thief


def _run_game(strats: dict[Role, Strategy], cfg: TrainConfig, rng: random.Random,
              *, learner: Role | None) -> Outcome:
    """Play one subgame; update the ``learner`` role's Q-values after each of its plies."""
    board = Board(cfg.grid, cfg.grid, 1, True)
    cop, thief = _start_cells(board, rng)
    game = Subgame(board, cop, thief, cfg.rounds, cfg.max_barriers)
    while not game.finished():
        role = game.turn
        opp = game.position_of(Role.THIEF if role is Role.COP else Role.COP)
        own = game.position_of(role)
        before = chebyshev(own, opp)
        obs = Observation(role, own, game.move_number, game.max_moves, game.barriers_left)
        game.apply(strats[role].decide(obs, opp, board))
        if role is learner:
            after = chebyshev(game.position_of(role), opp)
            strats[role].learn(shaped_reward(role, before, after, game.captured()))
    return game.outcome or Outcome.THIEF_WIN


def evaluate(q_cop, cfg: TrainConfig, rng: random.Random, games: int) -> float:
    """Greedy cop (using ``q_cop``) win-rate vs a fixed heuristic thief."""
    cop = QTableStrategy(cfg.learning_rate, cfg.discount, 0.0, rng)
    cop.q = q_cop.copy()
    strats = {Role.COP: cop, Role.THIEF: build_strategy({"kind": "heuristic"})}
    wins = sum(_run_game(strats, cfg, rng, learner=None) is Outcome.COP_WIN for _ in range(games))
    return wins / games


def train(cfg: TrainConfig, rng: random.Random | None = None) -> dict:
    """Train cop+thief Q-tables vs fixed heuristics; return the tables and learning curve."""
    rng = rng or random.Random(cfg.seed)
    cop = QTableStrategy(cfg.learning_rate, cfg.discount, cfg.eps_start, rng)
    thief = QTableStrategy(cfg.learning_rate, cfg.discount, cfg.eps_start, rng)
    h_thief = build_strategy({"kind": "heuristic"})
    h_cop = build_strategy({"kind": "heuristic", "cop_uses_barriers": True})
    curve: list[dict] = []
    for i in range(cfg.games):
        cop.epsilon = thief.epsilon = _epsilon(i, cfg.games, cfg.eps_start, cfg.eps_end)
        _run_game({Role.COP: cop, Role.THIEF: h_thief}, cfg, rng, learner=Role.COP)
        _run_game({Role.COP: h_cop, Role.THIEF: thief}, cfg, rng, learner=Role.THIEF)
        if (i + 1) % cfg.eval_every == 0:
            curve.append({
                "games": i + 1,
                "epsilon": round(cop.epsilon, 3),
                "cop_winrate_vs_heuristic": round(evaluate(cop.q, cfg, rng, cfg.eval_games), 3),
            })
    return {"q_cop": cop.q, "q_thief": thief.q, "curve": curve}
