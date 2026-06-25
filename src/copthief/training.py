"""Reinforcement-learning trainer: tabular Q-learning by self-play (no LLM, keyless).

Both agents run :class:`QTableStrategy` and learn online from a distance-shaped reward
(`shaped_reward`): the cop is rewarded for closing in, the thief for fleeing, with a large
terminal bonus/penalty on capture. Exploration anneals from ``eps_start`` to ``eps_end`` as
training progresses (explore early, exploit late). Every ``eval_every`` games the greedy cop
is measured against a fixed heuristic thief, yielding a learning curve.

Games run on a deliberately tight clock (small board, few rounds) so the cop cannot win by
default — a better-learned policy captures more often, making the curve informative.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from copthief.constants import Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.domain.subgame import Subgame
from copthief.strategy.base import chebyshev
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


def _run_game(strats: dict[Role, object], cfg: TrainConfig, rng: random.Random,
              *, learn: bool) -> Outcome:
    """Play one self-play subgame; update Q-values each ply when ``learn`` is set."""
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
        if learn:
            after = chebyshev(game.position_of(role), opp)
            strats[role].learn(shaped_reward(role, before, after, game.captured()))
    return game.outcome or Outcome.THIEF_WIN


def evaluate(q_cop, cfg: TrainConfig, rng: random.Random, games: int) -> float:
    """Greedy cop (using ``q_cop``) win-rate vs a fixed heuristic thief."""
    cop = QTableStrategy(cfg.learning_rate, cfg.discount, 0.0, rng)
    cop.q = q_cop.copy()
    strats = {Role.COP: cop, Role.THIEF: build_strategy({"kind": "heuristic"})}
    wins = sum(_run_game(strats, cfg, rng, learn=False) is Outcome.COP_WIN for _ in range(games))
    return wins / games


def train(cfg: TrainConfig, rng: random.Random | None = None) -> dict:
    """Train cop+thief Q-tables by self-play; return the tables and the learning curve."""
    rng = rng or random.Random(cfg.seed)
    cop = QTableStrategy(cfg.learning_rate, cfg.discount, cfg.eps_start, rng)
    thief = QTableStrategy(cfg.learning_rate, cfg.discount, cfg.eps_start, rng)
    strats = {Role.COP: cop, Role.THIEF: thief}
    curve: list[dict] = []
    for i in range(cfg.games):
        cop.epsilon = thief.epsilon = _epsilon(i, cfg.games, cfg.eps_start, cfg.eps_end)
        _run_game(strats, cfg, rng, learn=True)
        if (i + 1) % cfg.eval_every == 0:
            curve.append({
                "games": i + 1,
                "epsilon": round(cop.epsilon, 3),
                "cop_winrate_vs_heuristic": round(evaluate(cop.q, cfg, rng, cfg.eval_games), 3),
            })
    return {"q_cop": cop.q, "q_thief": thief.q, "curve": curve}
