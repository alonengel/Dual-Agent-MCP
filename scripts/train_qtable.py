"""Train tabular Q-learning agents by self-play and save the artifacts + learning curve.

Reinforcement learning, not LLM fine-tuning: the agents learn a value table from a
distance-shaped reward over many fast, keyless engine games. The README's §8 names
Q-learning as the recommended strategy path; this is its training rig.

Run:  uv run python scripts/train_qtable.py [--games 1000] [--grid 5] [--rounds 4]

Writes:
  results/qtable_cop.npy, results/qtable_thief.npy  - learned Q-tables (git-ignored)
  results/training_<ts>.json                        - config + learning curve
  assets/training_curve.png                         - cop win-rate vs training games
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

from copthief.training import TrainConfig, evaluate, train  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _config() -> TrainConfig:
    """Parse CLI flags into a TrainConfig."""
    p = argparse.ArgumentParser(description="Train Q-learning agents by self-play")
    p.add_argument("--games", type=int, default=1000)
    p.add_argument("--grid", type=int, default=5)
    p.add_argument("--rounds", type=int, default=4, help="round cap (tight => skill matters)")
    p.add_argument("--eval-every", type=int, default=100)
    p.add_argument("--eval-games", type=int, default=200)
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()
    return TrainConfig(games=a.games, grid=a.grid, rounds=a.rounds,
                       eval_every=a.eval_every, eval_games=a.eval_games, seed=a.seed)


def _plot(curve: list[dict], baseline: float, out: Path) -> None:
    """Render the cop win-rate learning curve with the untrained baseline."""
    games = [c["games"] for c in curve]
    win = [c["cop_winrate_vs_heuristic"] for c in curve]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(games, win, marker="o", label="trained cop")
    ax.axhline(baseline, ls="--", color="gray", label=f"untrained baseline ({baseline:.2f})")
    ax.set_xlabel("training games")
    ax.set_ylabel("cop win-rate vs heuristic thief")
    ax.set_ylim(0, 1)
    ax.set_title("Q-learning self-play: cop win-rate over training")
    ax.legend()
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=110)
    plt.close(fig)


def main() -> int:
    """Train, evaluate the untrained baseline, persist Q-tables + curve, and plot."""
    cfg = _config()
    print(f"training {cfg.games} games on {cfg.grid}x{cfg.grid}, rounds={cfg.rounds} ...")
    result = train(cfg)
    baseline = evaluate(np.zeros_like(result["q_cop"]), cfg, random.Random(cfg.seed + 1),
                        cfg.eval_games)

    results_dir = ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    np.save(results_dir / "qtable_cop.npy", result["q_cop"])
    np.save(results_dir / "qtable_thief.npy", result["q_thief"])
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    summary = {"config": vars(cfg), "baseline_winrate": round(baseline, 3),
               "curve": result["curve"]}
    (results_dir / f"training_{stamp}.json").write_text(json.dumps(summary, indent=2),
                                                        encoding="utf-8")
    _plot(result["curve"], baseline, ROOT / "assets" / "training_curve.png")

    print(f"baseline (untrained cop) win-rate vs heuristic: {baseline:.2f}")
    for c in result["curve"]:
        print(f"  games {c['games']:>5}  eps {c['epsilon']:.3f}  "
              f"cop win-rate {c['cop_winrate_vs_heuristic']:.2f}")
    final = result["curve"][-1]["cop_winrate_vs_heuristic"] if result["curve"] else float("nan")
    print(f"final trained cop win-rate vs heuristic: {final:.2f}")
    print("saved: results/qtable_cop.npy, results/qtable_thief.npy, assets/training_curve.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
