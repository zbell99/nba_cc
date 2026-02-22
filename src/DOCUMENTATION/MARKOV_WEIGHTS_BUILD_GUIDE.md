# Markov Weights Dataset Build Guide

## Overview
This document describes the creation of Markov transition weight datasets using the `pivot_game_state_data()` function from `src/build_markov_weights.py`. These datasets provide transition probability distributions for a Monte Carlo simulation engine.

---

## Goal
Transform the preprocessed game state snapshots (`data/nba_snapshot_data.parquet`) into a set of discrete Markov states, each with a probability distribution over possible next-state score changes (-5 to +5 points).

---

## Source Data
- **File**: `data/nba_snapshot_data.parquet`
- **Builder script**: `src/markov_data.py`
- **Row count**: ~1.4M snapshot rows (one per 15-second interval per game)

### Required Columns
| Column | Type | Purpose |
|---|---|---|
| `game_id` | int64 | Game identifier |
| `home_team_spread` | float64 | Pregame betting line |
| `time_elapsed` | float64 | Seconds since game start |
| `score_margin` | int64 | Score margin |

---

## Output Dataset
- **File**: `data/markov_weights_{time_pad}_{score_pad}_{odds_pad}_{time_cutoff}.parquet`
- **Builder script**: `src/build_markov_weights.py`
- **Format**: Parquet

### Output Columns
| Column | Type | Description |
|---|---|---|
| `time_elapsed` | float64 | Current game time (seconds) |
| `score_margin` | int64 | Current score margin (home - away) |
| `home_team_spread` | float64 | Current pregame spread |
| `sample_size` | int64 | Number of historical transitions for this state |
| `p-5` | float64 | P(next score_margin ≤ current - 5) |
| `p-4` | float64 | P(next score_margin = current - 4) |
| ... | ... | ... |
| `p+4` | float64 | P(next score_margin = current + 4) |
| `p+5` | float64 | P(next score_margin ≥ current + 5) |

---

## How It Works

### Step 1: Load and Filter Data
```python
df = game_state_data()  # Load snapshot parquet
df = df[df["time_elapsed"] <= time_cutoff]  # Exclude late-game rows
```

### Step 2: Identify Transitions
Sort by `game_id` and `time_elapsed`, then use `groupby().shift(-1)` to find the next 15-second snapshot's score within each game.

```python
df = df.sort_values(["game_id", "time_elapsed"])
df["next_score_margin"] = df.groupby("game_id")["score_margin"].shift(-1)
df = df.dropna(subset=["next_score_margin"])  # Remove final snapshots (no transition)
```

### Step 3: Compute Score Changes
Calculate the margin change and clip to [-5, 5] so transitions fit into discrete buckets.

```python
df["score_change"] = (df["next_score_margin"] - df["score_margin"]).clip(-5, 5).astype(int)
```

### Step 4: Padding Windows (Sample Size Aggregation)
For each unique game state, compute a window around it using padding parameters:

- **time_padding**: seconds ±
- **score_padding**: points ±
- **odds_padding**: points ±

For example, with `score_padding=2`, the state at score_margin=10 will aggregate historical data from states with score_margin ∈ [8, 12].

### Step 5: Count Transitions
For each state and its padded window:
1. Find all historical rows matching the window (vectorized boolean indexing)
2. Count transitions into each bucket (-5 to +5)
3. Divide by `sample_size` to get probabilities
4. **Show progress in terminal using a progress bar (`tqdm`) during concurrent processing**

---

## Key Design Decisions

### Why Padding?
Padding windows increase sample size for each state. Without padding, rare states (e.g., specific time + spread + score combinations) would have few or zero historical transitions. Padding trades state precision for statistical robustness.

### Why Clip to [-5, 5]?
Limiting buckets keeps the output compact while capturing the vast majority of transitions. In real games, score changes >5 in a 15-second interval are rare.

### Why Parquet?
- Smaller file size (~10x compression vs CSV)
- Fast sequential reads for simulation lookups
- Preserves dtypes exactly

### Why Not Discretize States?
We keep each unique observed `(time_elapsed, score_margin, spread)` as a separate row, then use padding windows to enrich sample size during simulation. This preserves data resolution while allowing flexible padding choices.

### Why Progress Bar?
- Provides real-time feedback for long-running concurrent operations
- Helps verify script is running and estimate completion time

---

## Running the Script

```bash
source nba-cc-env/bin/activate
python src/build_markov_weights.py
```

**Output:**
```
Loading game state data...
  1,452,980 snapshot rows
Pivoting to Markov weights...
Computing Markov weights: 100%|████████████████████████████████████| 153420/153420 [01:23<00:00, 1842.12it/s]
  153,420 unique states with weights
time_elapsed: 1440.0
score_margin: 10
home_team_spread: -3.5
sample_size: 847
p-5: 0.012
p-4: 0.010
... (through p+5)
Saving to .../data/markov_weights_0_0_0.5_5000.0.parquet ...
```

> **Note:**  
> The script uses `tqdm` to display a progress bar for concurrent computation of Markov weights.  
> Install with `pip install tqdm` if needed.


### Configuration
Edit the parameters in `main()` to change padding:

```python
time_padding = 0      # seconds
score_padding = 0     # points
odds_padding = 0.5    # points
time_cutoff = 5000.0  # seconds
```

Higher padding → Larger sample sizes per state, but less distinct distributions.

---

## Usage in Monte Carlo Simulation

Load and query efficiently:

```python
import pandas as pd
import numpy as np

weights = pd.read_parquet("data/markov_weights_0_0_0.5_5000.0.parquet")

# Look up a state
state = weights[
    (weights["time_elapsed"] == 1440.0) &
    (weights["score_margin"] == 10) &
    (weights["home_team_spread"] == -3.5)
]

# Extract probabilities
probs = state[["p-5", "p-4", "p-3", "p-2", "p-1", "p+0", 
               "p+1", "p+2", "p+3", "p+4", "p+5"]].values[0]

# Sample next score change
next_change = np.random.choice(range(-5, 6), p=probs)
new_score_margin = current_score_margin + next_change
```

---

## Iteration History

1. **Initial approach**: Discretized states using rounding (e.g., round times to nearest 15 seconds). This lost precision.
2. **Refined approach**: Keep all observed states, use value-range padding windows to aggregate sample size without losing resolution. Allows flexible padding tuning post-hoc.
3. **Performance**: Vectorized filtering with boolean indexing is fast enough for typical padding choices (thousands of states).

---

## Notes

- The function accepts the raw snapshot dataframe as input; it computes `score_margin` internally if missing.
- Final snapshots within each game are dropped (no next state to transition to).
- States with zero historical transitions will have NaN → 0.0 zero probabilities for unobserved buckets.
- Sample size varies by padding; use this metric to assess state robustness during simulation validation.
