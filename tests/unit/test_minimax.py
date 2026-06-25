"""Tests for the depth-N MinimaxStrategy (generalises the depth-1 lookahead)."""

from __future__ import annotations

from copthief.constants import Action, Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation, Position
from copthief.domain.subgame import Subgame
from copthief.strategy.base import chebyshev
from copthief.strategy.factory import build_strategy
from copthief.strategy.lookahead import LookaheadStrategy
from copthief.strategy.minimax import MinimaxStrategy


def _obs(role: Role, here: Position, mn: int = 0, max_moves: int = 25) -> Observation:
    return Observation(role, here, mn, max_moves, 5)


def _play(cop, thief, c: Position, t: Position, rounds: int) -> Outcome:
    """Run one move-only subgame to its outcome."""
    board = Board(5, 5, 1, True)
    game = Subgame(board, c, t, rounds, 5)
    strats = {Role.COP: cop, Role.THIEF: thief}
    while not game.finished():
        role = game.turn
        opp = game.position_of(Role.THIEF if role is Role.COP else Role.COP)
        own = game.position_of(role)
        obs = Observation(role, own, game.move_number, game.max_moves, game.barriers_left)
        game.apply(strats[role].decide(obs, opp, board))
    return game.outcome or Outcome.THIEF_WIN


def test_factory_builds_minimax_with_configured_depth() -> None:
    strat = build_strategy({"kind": "minimax", "minimax": {"depth": 4}})
    assert isinstance(strat, MinimaxStrategy) and strat.depth == 4


def test_depth_is_clamped_to_at_least_one() -> None:
    assert MinimaxStrategy(depth=0).depth == 1


def test_cop_captures_adjacent_thief(board: Board) -> None:
    move = MinimaxStrategy().decide(_obs(Role.COP, Position(2, 2)), Position(3, 3), board)
    assert move.action is Action.MOVE and (move.dx, move.dy) == (1, 1)


def test_cop_closes_in(board: Board) -> None:
    move = MinimaxStrategy().decide(_obs(Role.COP, Position(1, 1)), Position(5, 5), board)
    new = Position(1 + move.dx, 1 + move.dy)
    assert chebyshev(new, Position(5, 5)) < chebyshev(Position(1, 1), Position(5, 5))


def test_thief_keeps_its_distance(board: Board) -> None:
    move = MinimaxStrategy().decide(_obs(Role.THIEF, Position(3, 3)), Position(2, 2), board)
    new = Position(3 + move.dx, 3 + move.dy)
    assert chebyshev(new, Position(2, 2)) >= chebyshev(Position(3, 3), Position(2, 2))


def test_stays_when_boxed_in() -> None:
    board = Board(1, 1, origin=1, diagonal=True)
    move = MinimaxStrategy().decide(_obs(Role.THIEF, Position(1, 1)), Position(1, 1), board)
    assert move.action is Action.STAY


def test_minimax_cop_solves_the_benchmark() -> None:
    """A deep minimax cop forces capture from *every* start within the 4-round budget.

    The 5x5 / 4-round game is a forced cop win, so the optimal pursuer captures any thief;
    we verify it against the deterministic lookahead thief over all 600 distinct starts.
    """
    cells = [Position(x, y) for x in range(1, 6) for y in range(1, 6)]
    starts = [(c, t) for c in cells for t in cells if c != t]
    cop = MinimaxStrategy(depth=8)
    wins = sum(_play(cop, LookaheadStrategy(), c, t, rounds=4) is Outcome.COP_WIN
               for c, t in starts)
    assert wins == len(starts)  # 600/600 — the game is solved


def test_minimax_cop_beats_depth1_lookahead_cop() -> None:
    """Deeper search strictly dominates the depth-1 lookahead on the same benchmark."""
    cells = [Position(x, y) for x in range(1, 6) for y in range(1, 6)]
    starts = [(c, t) for c in cells for t in cells if c != t]
    deep = sum(_play(MinimaxStrategy(8), LookaheadStrategy(), c, t, 4) is Outcome.COP_WIN
               for c, t in starts)
    shallow = sum(_play(LookaheadStrategy(), LookaheadStrategy(), c, t, 4) is Outcome.COP_WIN
                  for c, t in starts)
    assert deep > shallow
