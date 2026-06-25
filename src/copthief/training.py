"""Reinforcement-learning trainer: Q-learning vs a fixed heuristic opponent.

Each learner trains against a *stationary* heuristic opponent of the other role (rather than
co-adapting self-play, which gives a moving target and a noisy curve): the cop learns to
capture a heuristic thief, the thief to evade a heuristic cop. Rewards are distance-shaped
(`shaped_reward`) with a terminal capture bonus/penalty; exploration anneals from `eps_start`
to `eps_end`. Every `eval_every` games the greedy cop is measured against the heuristic thief.

The loop is policy-agnostic: :func:`train` learns a tabular Q-table (board-region state) and
:func:`train_linear` learns a linear afterstate value over hand-built features
(:mod:`copthief.strategy.linear_q`). Games run on a deliberately tight clock so the cop cannot
win by default — a better-learned policy captures more often. Full analysis in README §9.1.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from copthief.constants import Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.domain.subgame import Subgame
from copthief.strategy.base import Strategy, chebyshev
from copthief.strategy.factory import build_strategy
from copthief.strategy.linear_q import LinearQStrategy
from copthief.strategy.qlearning import QTableStrategy, shaped_reward


@dataclass
class TrainConfig:
    """Hyper-parameters for a training run (all overridable from the CLI)."""

    games: int = 1000
    grid: int = 5
    rounds: int = 4          # tight clock: the cop must capture quickly, so skill shows
    max_barriers: int = 5
    learning_rate: float = 0.1  # steadier convergence for the larger board-aware Q-table
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
    if learner is not None and hasattr(strats[learner], "end_episode"):
        strats[learner].end_episode()  # Monte-Carlo learners settle up at episode end
    return game.outcome or Outcome.THIEF_WIN


def evaluate_strategy(cop: Strategy, cfg: TrainConfig, rng: random.Random, games: int) -> float:
    """Greedy win-rate of a trained ``cop`` strategy vs a fixed heuristic thief."""
    saved = cop.epsilon  # type: ignore[attr-defined]
    cop.epsilon = 0.0    # type: ignore[attr-defined]
    strats = {Role.COP: cop, Role.THIEF: build_strategy({"kind": "heuristic"})}
    wins = sum(_run_game(strats, cfg, rng, learner=None) is Outcome.COP_WIN for _ in range(games))
    cop.epsilon = saved  # type: ignore[attr-defined]
    return wins / games


def evaluate(q_cop, cfg: TrainConfig, rng: random.Random, games: int) -> float:
    """Greedy cop win-rate from a raw Q-table ``q_cop`` (back-compat array entry point)."""
    cop = QTableStrategy(cfg.learning_rate, cfg.discount, 0.0, rng)
    cop.q = q_cop.copy()
    return evaluate_strategy(cop, cfg, rng, games)


def _train(cfg: TrainConfig, rng: random.Random,
           make: Callable[[float], Strategy]) -> tuple[Strategy, Strategy, list[dict]]:
    """Generic train loop: each role learns vs a fixed heuristic; returns (cop, thief, curve)."""
    cop, thief = make(cfg.eps_start), make(cfg.eps_start)
    h_thief = build_strategy({"kind": "heuristic"})
    h_cop = build_strategy({"kind": "heuristic", "cop_uses_barriers": True})
    curve: list[dict] = []
    for i in range(cfg.games):
        cop.epsilon = thief.epsilon = _epsilon(i, cfg.games, cfg.eps_start, cfg.eps_end)
        _run_game({Role.COP: cop, Role.THIEF: h_thief}, cfg, rng, learner=Role.COP)
        _run_game({Role.COP: h_cop, Role.THIEF: thief}, cfg, rng, learner=Role.THIEF)
        if (i + 1) % cfg.eval_every == 0:
            curve.append({"games": i + 1, "epsilon": round(cop.epsilon, 3),
                          "cop_winrate_vs_heuristic":
                              round(evaluate_strategy(cop, cfg, rng, cfg.eval_games), 3)})
    return cop, thief, curve


def train(cfg: TrainConfig, rng: random.Random | None = None) -> dict:
    """Train tabular Q-tables vs fixed heuristics; return the tables and learning curve."""
    rng = rng or random.Random(cfg.seed)
    cop, thief, curve = _train(
        cfg, rng, lambda eps: QTableStrategy(cfg.learning_rate, cfg.discount, eps, rng))
    return {"q_cop": cop.q, "q_thief": thief.q, "curve": curve}


def train_linear(cfg: TrainConfig, rng: random.Random | None = None) -> dict:
    """Train linear afterstate-feature policies vs fixed heuristics; return weights + curve."""
    rng = rng or random.Random(cfg.seed)
    cop, thief, curve = _train(
        cfg, rng, lambda eps: LinearQStrategy(cfg.learning_rate, cfg.discount, eps, rng))
    return {"w_cop": cop.weights, "w_thief": thief.weights, "curve": curve}
