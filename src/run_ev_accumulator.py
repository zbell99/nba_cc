"""Orchestrator for accumulating per-state EV estimates into wpa_challenge_values_sim.parquet.

Adaptive fill strategy
----------------------
For each spread, the script works **layer by layer** through time steps (0, 45, 90, …).
At each time step it checks which (gt, m) states are below their tiered target,
then launches exactly the number of additional simulations needed from each
under-sampled starting point.  Simulations starting at (gt, m) also produce samples
for all *future* states they pass through, so later layers naturally benefit from
earlier work.

Tiered targets (by |score margin|):
    |m| <= 5   →  5 000 samples
    |m| <= 10  →  2 000 samples
    |m| <= 15  →  1 000 samples
    |m| <= 20  →    500 samples

Usage
-----
    # Fill all spreads with default tiered targets:
    python src/run_ev_accumulator.py

    # Override tier targets:
    python src/run_ev_accumulator.py --t1 10000 --t2 5000 --t3 2000 --t4 1000

    # Specific spreads only:
    python src/run_ev_accumulator.py --spreads -3 0 3

    # Resume after interruption (prior progress is preserved):
    python src/run_ev_accumulator.py
"""

import argparse
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import pandas as pd
import numpy as np
import concurrent.futures
from tqdm import tqdm

# ---------------------------------------------------------------------------
SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC_DIR))

from nba_game_sim import (
    read_markov_weights,
    load_wpa_data,
    MarkovWeights,
    _game_with_ev_data,
    MARKOV_WEIGHTS_PATH,
    WPA_SIM_PATH,
)

TIME_PER_STEP = 45


# ── helpers ────────────────────────────────────────────────────────────────
# ── Tiered target defaults ─────────────────────────────────────────────────
# (can be overridden via CLI)
DEFAULT_TIERS = {
    5:  5_000,   # |m| <= 5
    10: 2_000,   # |m| <= 10
    15: 1_000,   # |m| <= 15
    20:   500,   # |m| <= 20
}


def target_for_margin(m: int, tiers: dict[int, int]) -> int:
    """Return the sample-size target for a given score margin."""
    abs_m = abs(m)
    for bound in sorted(tiers.keys()):
        if abs_m <= bound:
            return tiers[bound]
    return tiers[max(tiers.keys())]  # fallback to widest tier


def max_margin_for_time(gt: float) -> int:
    """Return the maximum |m| reachable at game-time *gt*.

    Schedule:  t=0 → 0,  t=45 → 5,  t=90 → 10,  t=135 → 15,  t≥180 → 20.
    """
    return min(int(gt / TIME_PER_STEP) * 5, 20)


def load_sim_parquet(path: Path = WPA_SIM_PATH) -> pd.DataFrame:
    return pd.read_parquet(path)


def save_sim_parquet(df: pd.DataFrame, path: Path = WPA_SIM_PATH) -> None:
    df.to_parquet(path, index=False)


def submit_sims(
    executor: concurrent.futures.ProcessPoolExecutor,
    jobs: list[tuple[int, float, int, float]],
    mw: MarkovWeights,
    wpa_data: pd.DataFrame,
) -> dict[tuple[float, int], list]:
    """Submit all (n, gt, m, spread) jobs to a shared executor.

    *jobs* is a list of (count, initial_time, initial_margin, spread) tuples.
    Returns {(gt, m): [count, sum_v1, sum_v2]}  aggregated across every sim.
    """
    accum: dict[tuple, list] = defaultdict(lambda: [0, 0.0, 0.0])
    total = sum(j[0] for j in jobs)

    futures = []
    for count, gt, m, spread in jobs:
        for _ in range(count):
            futures.append(
                executor.submit(
                    _game_with_ev_data, gt, m, spread,
                    TIME_PER_STEP, mw, wpa_data,
                )
            )

    for f in tqdm(
        concurrent.futures.as_completed(futures),
        total=total,
        desc="    sims",
        leave=False,
    ):
        try:
            trajectory = f.result()
        except Exception as exc:
            print(f"      [warn] sim failed: {exc}")
            continue
        for gt, m, v1, v2 in trajectory:
            key = (gt, m)
            accum[key][0] += 1
            accum[key][1] += v1
            accum[key][2] += v2

    return dict(accum)


def merge_accum(sim_df: pd.DataFrame, spread: float, accum: dict) -> pd.DataFrame:
    """Running-average merge of batch results into the sim DataFrame."""
    spread_mask = sim_df["line"] == spread

    for (gt, m), (count, sum_v1, sum_v2) in accum.items():
        row_mask = spread_mask & (sim_df["gt"] == gt) & (sim_df["m"] == m)
        if not row_mask.any():
            continue

        idx = sim_df.index[row_mask]
        old_n   = sim_df.loc[idx, "sim_sample_size"].iloc[0]
        old_ev1 = sim_df.loc[idx, "ev1"].iloc[0]
        old_ev2 = sim_df.loc[idx, "ev2"].iloc[0]

        new_n   = old_n + count
        new_ev1 = (old_n * old_ev1 + sum_v1) / new_n
        new_ev2 = (old_n * old_ev2 + sum_v2) / new_n

        sim_df.loc[idx, "sim_sample_size"] = int(new_n)
        sim_df.loc[idx, "ev1"] = new_ev1
        sim_df.loc[idx, "ev2"] = new_ev2

    return sim_df


def fill_spread(
    spread: float,
    tiers: dict[int, int],
    mw: MarkovWeights,
    sim_df: pd.DataFrame,
    executor: concurrent.futures.ProcessPoolExecutor,
) -> pd.DataFrame:
    """Fill all states for one spread to their tiered targets, layer by layer.

    Layer 0 (t=0) always starts from m=0.  For subsequent layers, only states
    that have already been reached (sim_sample_size > 0) are topped up — this
    avoids wasting compute on unreachable margin/time combinations.

    All under-sampled margins at a given time layer are submitted to the shared
    *executor* in one batch for maximum throughput.
    """

    time_steps = sorted(sim_df.loc[sim_df["line"] == spread, "gt"].unique())

    for gt in time_steps:
        m_limit = max_margin_for_time(gt)
        layer = sim_df[
            (sim_df["line"] == spread)
            & (sim_df["gt"] == gt)
            & (sim_df["m"].abs() <= m_limit)
        ]

        # Build list of (count, gt, m, spread) jobs for this layer
        jobs: list[tuple[int, float, int, float]] = []

        for _, row in layer.iterrows():
            m = int(row["m"])
            target = target_for_margin(m, tiers)
            current_n = int(row["sim_sample_size"])

            if gt == 0 and m != 0:
                continue  # only m=0 is a valid starting point at t=0
            if gt > 0 and current_n == 0:
                continue  # hasn't been reached yet — don't force it

            needed = target - current_n
            if needed <= 0:
                continue

            jobs.append((needed, gt, m, spread))

        if not jobs:
            continue

        total_sims = sum(j[0] for j in jobs)
        margins = len(jobs)
        print(f"  t={gt:.0f}: {margins} margin(s) need filling — {total_sims:,} sims at time {datetime.now()}")

        accum = submit_sims(executor, jobs, mw, sim_df)
        sim_df = merge_accum(sim_df, spread, accum)

        # Save after each time layer for resumability
        save_sim_parquet(sim_df)

    return sim_df


# ── CLI ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Adaptively fill per-state EV estimates with tiered targets."
    )
    parser.add_argument(
        "--t1", type=int, default=DEFAULT_TIERS[5],
        help=f"Target for |m| <= 5  (default: {DEFAULT_TIERS[5]})",
    )
    parser.add_argument(
        "--t2", type=int, default=DEFAULT_TIERS[10],
        help=f"Target for |m| <= 10 (default: {DEFAULT_TIERS[10]})",
    )
    parser.add_argument(
        "--t3", type=int, default=DEFAULT_TIERS[15],
        help=f"Target for |m| <= 15 (default: {DEFAULT_TIERS[15]})",
    )
    parser.add_argument(
        "--t4", type=int, default=DEFAULT_TIERS[20],
        help=f"Target for |m| <= 20 (default: {DEFAULT_TIERS[20]})",
    )
    parser.add_argument(
        "--spreads", type=float, nargs="*", default=None,
        help="Spreads to process (default: all integers -15 … +15)",
    )
    args = parser.parse_args()

    tiers = {5: args.t1, 10: args.t2, 15: args.t3, 20: args.t4}
    print(f"Tiered targets: {tiers}")

    spreads = (
        [float(s) for s in args.spreads]
        if args.spreads is not None
        else [float(s) for s in range(-15, 16)]
    )

    # ── Load data once ──────────────────────────────────────────────────
    print("Loading Markov weights …")
    markov_weights = read_markov_weights(MARKOV_WEIGHTS_PATH)
    mw = MarkovWeights(markov_weights, time_gap=TIME_PER_STEP, score_gap=1, odds_gap=1.0)
    print(f"  {len(markov_weights):,} rows")

    print("Loading sim parquet (for accumulation) …")
    sim_df = load_sim_parquet()
    print(f"  {len(sim_df):,} rows")

    print(f"Start time {datetime.now()}")

    # ── Single persistent pool for entire run ───────────────────────────
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for spread in spreads:
            spread_rows = sim_df[sim_df["line"] == spread]
            # Check if any state is below its tier target
            below = sum(
                1 for _, r in spread_rows.iterrows()
                if int(r["sim_sample_size"]) < target_for_margin(int(r["m"]), tiers)
            )
            if below == 0:
                print(f"\nSpread {spread:+.0f}: all states at target — skipping")
                continue

            print(f"\nSpread {spread:+.0f}: {below} states below target")
            sim_df = fill_spread(spread, tiers, mw, sim_df, executor)

    # Final summary
    filled = (sim_df["sim_sample_size"] > 0).sum()
    total = len(sim_df)
    min_n = sim_df.loc[sim_df["sim_sample_size"] > 0, "sim_sample_size"].min() if filled > 0 else 0
    max_n = sim_df.loc[sim_df["sim_sample_size"] > 0, "sim_sample_size"].max() if filled > 0 else 0
    print(f"\nDone. {filled:,}/{total:,} states filled (sample sizes {min_n}–{max_n})")


if __name__ == "__main__":
    main()
