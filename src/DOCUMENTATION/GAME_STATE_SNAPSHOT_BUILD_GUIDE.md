# Game State Snapshot Dataset Build Guide

## Overview
This document describes the creation of `nba_snapshot_data.parquet` — a 15-second interval snapshot dataset derived from play-by-play data, designed as the base table for a Markov chain model of expected score margin.

---

## Goal
Take the raw play-by-play dataset (`data/nba_pbp_data.csv`, ~3.5M rows) and produce a clean, uniform time-series with one row per 15-second interval per game. This fixed-interval structure is necessary for defining discrete Markov states over time.

---

## Source Data
- **File**: `data/nba_pbp_data.csv`
- **Source**: sportsdataverse (`load_nba_pbp`, seasons 2020–2025)
- **Loader script**: `src/pbp_data.py`
- **Row count**: ~3,515,729 plays across 7,485 games

### Columns Used from PBP
| Column | Purpose |
|---|---|
| `game_id` | Game identifier |
| `home_team_spread` | Pregame betting line (constant per game) |
| `start_quarter_seconds_remaining` | Clock countdown within each period (720→0 regulation, 300→0 OT) |
| `period` | Period number (1–4 regulation, 5+ overtime) |
| `home_score` | Cumulative home score at each play |
| `away_score` | Cumulative away score at each play |

---

## Output Dataset
- **File**: `data/nba_snapshot_data.parquet`
- **Builder script**: `src/markov_data.py`
- **Row count**: 1,452,980 snapshot rows
- **Format**: Parquet (smaller and faster than CSV for downstream reads)

### Output Columns
| Column | Type | Description |
|---|---|---|
| `game_id` | int64 | Game identifier |
| `home_team_spread` | float64 | Pregame betting line (half-point lines) |
| `time_elapsed` | float64 | Seconds since game start, counting up (0, 15, 30, ...) |
| `period` | int64 | Period number at this snapshot |
| `home_score` | int64 | Home team score at this snapshot |
| `away_score` | int64 | Away team score at this snapshot |
| `score_margin` | int64 | `home_score - away_score` |

---

## How It Works

### Step 1: Load Only Needed Columns
Uses `pd.read_csv(usecols=...)` to avoid reading the full 60+ column CSV into memory.

### Step 2: Compute Continuous Time Elapsed
The raw data provides `start_quarter_seconds_remaining`, which counts down within each period:
- **Regulation (periods 1–4)**: 720 → 0 per quarter
- **Overtime (periods 5+)**: 300 → 0 per OT period

We convert to a continuous elapsed axis:
```
Periods 1–4:  time_elapsed = (period - 1) * 720 + (720 - quarter_remaining)
Periods 5+:   time_elapsed = 2880 + (period - 5) * 300 + (300 - quarter_remaining)
```

This gives a monotonically increasing time axis from 0 through end of game (including overtime).

### Step 3: Build 15-Second Interval Grid per Game
For each game, create a uniform grid from 0 to the game's max elapsed time (rounded up to the next 15-second boundary).

### Step 4: Align Scores via `merge_asof`
Use `pd.merge_asof(direction="backward")` to map each 15-second interval to the most recent play's score. This effectively forward-fills the last known score into each interval.

### Step 5: Handle Edge Cases
- **Game start (time=0)**: Forward-fill with 0-0 score, period 1
- **Overtime games**: Intervals extend naturally beyond 2880 seconds
- **Decimal clock values**: End-of-quarter plays can have fractional seconds; the interval grid uses float64 to match
- **Simultaneous plays** (e.g., free throws at same timestamp): Pandas stable sort preserves original play order, so the last play's score is used

---

## Key Design Decisions

### Why `start_quarter_seconds_remaining` instead of `start_game_seconds_remaining`?
The `start_game_seconds_remaining` column resets to 0–300 for every OT period rather than continuing a global countdown. Using `start_quarter_seconds_remaining` + `period` gives us full control to build the correct continuous elapsed time.

### Why time elapsed (count up) instead of seconds remaining (count down)?
User preference — the Markov chain transitions move forward through the game and removes confusion with overtime periods.

### Why Parquet over CSV?
- Smaller file size (~5x compression)
- Faster reads for pandas/pyarrow
- Preserves column dtypes exactly (no re-inference on load)

### Why not include lagged features in this dataset?
The Markov property states that the next state depends only on the current state. Lagged features are better derived on-the-fly during modeling to keep this base table simple, reproducible, and flexible for experimentation (e.g., testing 2nd-order chains later).

---

## Running the Script

```bash
source nba-cc-env/bin/activate
python src/markov_data.py
```

Output:
```
Loading play-by-play data...
  3,515,729 plays across 7,485 games
Computing time elapsed...
Building 15-second snapshots...
  1,452,980 snapshot rows
Saving to .../data/nba_snapshot_data.parquet ...
Done.
```

---

## Iteration History

1. **Initial attempt** used `start_game_seconds_remaining` with a per-game max inversion. This was incorrect because OT periods reset to 0–300 rather than continuing a global countdown.
2. **Also loaded `end_game_seconds_remaining`** — removed as unused dead code.
3. **dtype mismatch**: The interval grid was int64 but `time_elapsed` was float64 (due to decimal clock values). Fixed by casting the grid to float.
4. **Final version** uses `start_quarter_seconds_remaining` + `period` for correct continuous elapsed time across regulation and overtime.
