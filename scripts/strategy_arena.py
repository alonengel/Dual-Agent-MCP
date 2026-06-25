"""Strategy arena: quantify how the move policies compare — no LLM, fast and free.

Plays many subgames for every (cop policy x thief policy) pairing with strategy-driven
moves under perfect information, isolating raw policy strength from LLM/dialogue and
partial observation. Prints a cop win-rate matrix and the average capture length. This
is the evidence behind "lookahead is the strongest policy" and a quick board-balance
check for the report.

Run:  uv run python scripts/strategy_arena.py [--games 60] [--grid 5] [--rounds 25]
"""

from __future__ import annotations

import argparse
import random

from copthief.constants import Outcome, Role
from copthief.domain.board import Board
from copthief.domain.models import Observation
from copthief.domain.subgame import Subgame
from copthief.strategy.factory import build_strategy

KINDS = ("heuristic", "adaptive", "lookahead", "minimax")


def _start_cells(board: Board, rng: random.Random) -> tuple:
    """Two distinct random free cells for the cop and the thief."""
    cop = board.random_free_cell(rng, exclude=set())
    thief = board.random_free_cell(rng, exclude={cop.as_tuple()})
    return cop, thief


def play_subgame(cop_kind: str, thief_kind: str, grid: int, rounds: int,
                 max_barriers: int, rng: random.Random) -> tuple[Outcome, int]:
    """Play one perfect-information subgame; return its outcome and capture move."""
    board = Board(grid, grid, 1, True)
    cop_pos, thief_pos = _start_cells(board, rng)
    game = Subgame(board, cop_pos, thief_pos, rounds, max_barriers)
    policies = {
        Role.COP: build_strategy({"kind": cop_kind, "cop_uses_barriers": True}, rng),
        Role.THIEF: build_strategy({"kind": thief_kind}, rng),
    }
    while not game.finished():
        role = game.turn
        opponent = game.position_of(Role.THIEF if role is Role.COP else Role.COP)
        obs = Observation(role, game.position_of(role), game.move_number, rounds,
                          game.barriers_left)
        game.apply(policies[role].decide(obs, opponent, game.board))
    return game.outcome or Outcome.THIEF_WIN, game.move_number


def run_matchup(cop_kind: str, thief_kind: str, games: int, grid: int, rounds: int,
                rng: random.Random) -> tuple[float, float]:
    """Return (cop win-rate, average capture move) over ``games`` subgames."""
    wins, capture_moves = 0, []
    for _ in range(games):
        outcome, moves = play_subgame(cop_kind, thief_kind, grid, rounds, 5, rng)
        if outcome is Outcome.COP_WIN:
            wins += 1
            capture_moves.append(moves)
    avg = sum(capture_moves) / len(capture_moves) if capture_moves else float("nan")
    return wins / games, avg


def _print_matrix(title: str, rows: dict[str, dict[str, str]]) -> None:
    """Print a labelled cop(row) x thief(col) table."""
    cols = KINDS
    head = "cop \\ thief".ljust(14) + "".join(f"{c:>14}" for c in cols)
    print(f"\n{title}\n{head}\n" + "-" * len(head))
    for cop_kind in cols:
        line = f"cop:{cop_kind}".ljust(14) + "".join(f"{rows[cop_kind][t]:>14}" for t in cols)
        print(line)


def main(argv: list[str] | None = None) -> int:
    """Run the full arena and print win-rate + capture-length matrices."""
    parser = argparse.ArgumentParser(description="Compare cop/thief move policies")
    parser.add_argument("--games", type=int, default=60, help="subgames per matchup")
    parser.add_argument("--grid", type=int, default=5, help="square board size")
    parser.add_argument("--rounds", type=int, default=25, help="max moves before survival")
    parser.add_argument("--seed", type=int, default=7, help="RNG seed")
    args = parser.parse_args(argv)
    rng = random.Random(args.seed)

    rates: dict[str, dict[str, str]] = {c: {} for c in KINDS}
    lengths: dict[str, dict[str, str]] = {c: {} for c in KINDS}
    for cop_kind in KINDS:
        for thief_kind in KINDS:
            rate, avg = run_matchup(cop_kind, thief_kind, args.games, args.grid,
                                    args.rounds, rng)
            rates[cop_kind][thief_kind] = f"{rate * 100:.0f}%"
            lengths[cop_kind][thief_kind] = "-" if avg != avg else f"{avg:.1f}"

    print(f"Strategy arena — {args.games} subgames/pairing, "
          f"{args.grid}x{args.grid} board, {args.rounds} rounds, perfect info")
    _print_matrix("Cop win-rate (higher = stronger cop / weaker thief):", rates)
    _print_matrix("Average capture move when the cop wins (lower = faster):", lengths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
