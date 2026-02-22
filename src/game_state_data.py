"""
Build a 15-second interval snapshot dataset from NBA play-by-play data.

For each game, produces one row per 15-second interval of elapsed game time
(including overtime), with forward-filled scores.

Output columns:
    game_id, home_team_spread, time_elapsed, period, home_score, away_score, score_margin
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PBP_PATH = PROJECT_ROOT / "data" / "nba_pbp_data.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "nba_snapshot_data.parquet"

# ── Config ───────────────────────────────────────────────────────────────────
SNAPSHOT_INTERVAL = 15  # seconds
REGULATION_SECONDS = 2880  # 48 min * 60
OT_PERIOD_SECONDS = 300  # 5 min * 60


QUARTER_SECONDS = 720  # 12 min * 60


def load_pbp(path: Path = PBP_PATH) -> pd.DataFrame:
    """Load play-by-play CSV with only the columns we need."""
    usecols = [
        "game_id",
        "home_team_spread",
        "start_quarter_seconds_remaining",
        "period",
        "home_score",
        "away_score",
    ]
    df = pd.read_csv(path, usecols=usecols)
    return df


def compute_time_elapsed(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive time_elapsed (seconds from game start, counting up).

    Uses start_quarter_seconds_remaining (counts down within each period) and
    period number to compute a continuous elapsed-time axis.

    Periods 1-4 (regulation): 720 seconds each.
    Periods 5+  (overtime):   300 seconds each.

    Note: start_quarter_seconds_remaining can contain decimals for end-of-quarter
    plays, so time_elapsed is float.
    """
    period = df["period"]
    qtr_remaining = df["start_quarter_seconds_remaining"]

    # Elapsed time at start of each period
    # Periods 1-4: (period-1) * 720
    # Period  5+:  2880 + (period-5) * 300
    is_reg = period <= 4
    period_start = np.where(
        is_reg,
        (period - 1) * QUARTER_SECONDS,
        REGULATION_SECONDS + (period - 5) * OT_PERIOD_SECONDS,
    )

    # Duration of the current period
    period_duration = np.where(is_reg, QUARTER_SECONDS, OT_PERIOD_SECONDS)

    df["time_elapsed"] = period_start + (period_duration - qtr_remaining)
    return df


def build_snapshots(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each game, create a row at every 15-second interval from 0 to end,
    with forward-filled scores.
    """
    snapshots = []

    for game_id, gdf in df.groupby("game_id"):
        gdf = gdf.sort_values("time_elapsed")

        # Game metadata (constant per game)
        spread = gdf["home_team_spread"].iloc[0]

        # Maximum elapsed time in game (round up to next interval)
        max_elapsed = gdf["time_elapsed"].max()
        max_interval = int(np.ceil(max_elapsed / SNAPSHOT_INTERVAL)) * SNAPSHOT_INTERVAL

        # Build interval grid (float to match time_elapsed dtype)
        intervals = np.arange(
            0, max_interval + SNAPSHOT_INTERVAL, SNAPSHOT_INTERVAL, dtype=float
        )

        # Use merge_asof to align each interval to the most recent play
        interval_df = pd.DataFrame({
            "time_elapsed": intervals,
            "game_id": game_id,
        })

        # Keep only the columns we need for the asof merge
        plays = gdf[["time_elapsed", "home_score", "away_score", "period"]].copy()
        plays = plays.sort_values("time_elapsed")

        # merge_asof: for each interval, grab the last play at or before that time
        merged = pd.merge_asof(
            interval_df.sort_values("time_elapsed"),
            plays,
            on="time_elapsed",
            direction="backward",
        )

        # Fill the very start (time_elapsed=0) if no play has occurred yet
        merged["home_score"] = merged["home_score"].ffill().fillna(0).astype(int)
        merged["away_score"] = merged["away_score"].ffill().fillna(0).astype(int)
        merged["period"] = merged["period"].ffill().fillna(1).astype(int)

        merged["home_team_spread"] = spread
        merged["score_margin"] = merged["home_score"] - merged["away_score"]

        snapshots.append(merged)

    result = pd.concat(snapshots, ignore_index=True)

    # Final column order
    result = result[
        [
            "game_id",
            "home_team_spread",
            "time_elapsed",
            "period",
            "home_score",
            "away_score",
            "score_margin",
        ]
    ]
    return result


def main():
    print("Loading play-by-play data...")
    df = load_pbp()
    print(f"  {len(df):,} plays across {df['game_id'].nunique():,} games")

    print("Computing time elapsed...")
    df = compute_time_elapsed(df)

    print("Building 15-second snapshots...")
    snapshots = build_snapshots(df)
    print(f"  {len(snapshots):,} snapshot rows")

    print(f"Saving to {OUTPUT_PATH} ...")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    snapshots.to_parquet(OUTPUT_PATH, index=False)

    # Quick summary
    print("\nSample rows:")
    print(snapshots.head(15).to_string(index=False))
    print(f"\nDone. Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
