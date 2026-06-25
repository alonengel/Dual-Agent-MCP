"""Train Q-learning agents (tabular or linear) vs a fixed heuristic, save curve + artifacts.

Reinforcement learning, not LLM fine-tuning: the agents learn a value function from a
distance-shaped reward over many fast, keyless engine games. Two policies:

* ``--policy qtable`` (default) — a tabular Q-table over a board-region state.
* ``--policy linear``           — linear value over afterstate features (the strongest:
                                  beats the lookahead minimax; see README §9.1).

Run:  uv run python scripts/train_qtable.py [--policy linear] [--games 50000]

Writes (all git-ignored except the PNG):
  results/<policy>_cop.npy, results/<policy>_thief.npy  - learned parameters
  results/training_<ts>.json                            - config + learning curve
  assets/training_curve.png                             - cop win-rate vs training games
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless plotting (set before pyplot is imported)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from copthief.strategy.linear_q import LinearQStrategy  # noqa: E402
from copthief.training import (  # noqa: E402
    TrainConfig,
    evaluate,
    evaluate_strategy,
    train,
    train_linear,
)

ROOT = Path(__file__).resolve().parent.parent


def _config() -> tuple[TrainConfig, str]:
    """Parse CLI flags into a (TrainConfig, policy) pair."""
    p = argparse.ArgumentParser(description="Train Q-learning agents vs a fixed heuristic")
    p.add_argument("--policy", choices=["qtable", "linear"], default="qtable")
    p.add_argument("--games", type=int, default=1000)
    p.add_argument("--grid", type=int, default=5)
    p.add_argument("--rounds", type=int, default=4, help="round cap (tight => skill matters)")
    p.add_argument("--learning-rate", type=float, default=None, help="default: 0.1 table / 0.05 linear")
    p.add_argument("--eval-every", type=int, default=100)
    p.add_argument("--eval-games", type=int, default=200)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()
    lr = a.learning_rate if a.learning_rate is not None else (0.05 if a.policy == "linear" else 0.1)
    cfg = TrainConfig(games=a.games, grid=a.grid, rounds=a.rounds, learning_rate=lr,
                      eval_every=a.eval_every, eval_games=a.eval_games, seed=a.seed)
    return cfg, a.policy


def _baseline(policy: str, result: dict, cfg: TrainConfig, rng: random.Random) -> float:
    """Win-rate of the untrained (zero-parameter) cop — the learning-curve floor."""
    if policy == "linear":
        base = LinearQStrategy(cfg.learning_rate, cfg.discount, 0.0)
        base.weights = np.zeros_like(result["w_cop"])
        return evaluate_strategy(base, cfg, rng, cfg.eval_games)
    return evaluate(np.zeros_like(result["q_cop"]), cfg, rng, cfg.eval_games)


def _plot(curve: list[dict], baseline: float, policy: str, out: Path) -> None:
    """Render the cop win-rate learning curve with the untrained baseline."""
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([c["games"] for c in curve], [c["cop_winrate_vs_heuristic"] for c in curve],
            marker="o", label=f"trained cop ({policy})")
    ax.axhline(baseline, ls="--", color="gray", label=f"untrained baseline ({baseline:.2f})")
    ax.axhline(0.66, ls=":", color="tab:green", label="lookahead minimax (0.66)")
    ax.set_xlabel("training games")
    ax.set_ylabel("cop win-rate vs heuristic thief")
    ax.set_ylim(0, 1)
    ax.set_title(f"Q-learning ({policy}): cop win-rate over training")
    ax.legend()
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    plt.close(fig)


def main() -> int:
    """Train the chosen policy, persist parameters + curve, and plot."""
    cfg, policy = _config()
    print(f"training {policy} for {cfg.games} games on {cfg.grid}x{cfg.grid}, "
          f"rounds={cfg.rounds}, lr={cfg.learning_rate} ...")
    result = train_linear(cfg) if policy == "linear" else train(cfg)
    baseline = _baseline(policy, result, cfg, random.Random(cfg.seed + 1))

    results_dir = ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    cop_key, thief_key = ("w_cop", "w_thief") if policy == "linear" else ("q_cop", "q_thief")
    np.save(results_dir / f"{policy}_cop.npy", result[cop_key])
    np.save(results_dir / f"{policy}_thief.npy", result[thief_key])
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    summary = {"policy": policy, "config": vars(cfg), "baseline_winrate": round(baseline, 3),
               "curve": result["curve"]}
    (results_dir / f"training_{stamp}.json").write_text(json.dumps(summary, indent=2),
                                                        encoding="utf-8")
    _plot(result["curve"], baseline, policy, ROOT / "assets" / "training_curve.png")

    print(f"baseline (untrained cop) win-rate vs heuristic: {baseline:.2f}")
    for c in result["curve"]:
        print(f"  games {c['games']:>6}  eps {c['epsilon']:.3f}  "
              f"cop win-rate {c['cop_winrate_vs_heuristic']:.2f}")
    final = result["curve"][-1]["cop_winrate_vs_heuristic"] if result["curve"] else float("nan")
    print(f"final {policy} cop win-rate vs heuristic: {final:.2f}  (lookahead minimax = 0.66)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
