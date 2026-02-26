# Game Simulation & Coach's Challenge Valuation Guide

## Overview
`nba_game_sim.py` contains two coupled models:

1. **Markov Chain Game Simulation** — samples realistic score trajectories from any starting state using precomputed transition probabilities.
2. **Coach's Challenge Valuation (Backward DP)** — given a simulated game with Poisson-sampled challengeable calls, computes the expected WPA value of optimally holding 1 or 2 challenges at every point in the game.

---

## Model 1: Markov Chain Game Simulation

### State Space
A game state is defined by three variables:

| Variable | Description | Discretization |
|---|---|---|
| `time_elapsed` | Seconds since tipoff (0 → 2760) | Aligned to `time_gap` (default 120s) |
| `score_margin` | Home score − Away score | Aligned to `score_gap` (default 2), clipped to [−20, +20] |
| `home_team_spread` | Pregame betting line (fixed for the game) | Aligned to `odds_gap` (default 2.0), half-point anchored |

### Transition Mechanism
At each 15-second step, the simulation:

1. **Aligns** the current `(time_elapsed, score_margin, spread)` to the nearest Markov weight bucket via rounding.
2. **Looks up** the precomputed probability distribution over score margin changes Δ ∈ {−5, −4, ..., +4, +5} for that state.
3. **Samples** a score margin change from that distribution.
4. **Advances** time by `time_per_step` (15 seconds) and applies the margin change.

The Markov weights are stored in `data/markov_weights_*.parquet`, with columns `p-5` through `p+5` representing the 11 possible margin-change probabilities for each state.

### Alignment Functions
Continuous game values are snapped to the discrete state grid before lookup:

- **Spread**: `aligned = 0.5 + round((spread − 0.5) / odds_gap) × odds_gap`
- **Score margin**: `aligned = round(margin / score_gap) × score_gap`
- **Time**: `aligned = round(time / time_gap) × time_gap`

### Simulation Loop
The simulation runs from the initial state until `time_elapsed` reaches `time_cutoff` (default 2760s = 46 minutes of game time), producing a list of `GameState` objects at 15-second intervals.

---

## Model 2: Coach's Challenge Valuation

### Background
In the NBA, each team starts the game with one coach's challenge. If they win their first challenge (successful overturn), they receive a second. This creates a two-tier decision problem: using a challenge on a marginal call forfeits the option value of saving it for a higher-value opportunity later.

### Inputs
Each `GameState` carries a list of `ChallengeableCall` objects, each with:
- **`type`** — a `ChallengeType` enum value representing the category of challengeable call (e.g., `ChallengeType.NOFOUL2_KEEPBALL`, `ChallengeType.OOB`, `ChallengeType.NOGOALTEND`). The enum's `.value` attribute provides the JSON key (e.g., `"nofoul2_keepBall"`, `"oob_challenge"`).
- **`confidence`** — the team's estimated probability of a successful overturn (0–1)

The **WPA** (Win Probability Added) for each challenge type at a given game state is looked up from `data/wpa_challenge_values.json`, a nested dictionary keyed by `spread → time_elapsed → score_margin → challenge_type.value → wpa`.

### Challenge State Transitions

| Challenges Remaining | Action | Win (prob = `confidence`) | Lose (prob = `1 − confidence`) |
|---|---|---|---|
| 2 (never used) | Use | Gain WPA, drop to 1 remaining | Gain nothing, drop to 0 remaining |
| 1 | Use | Gain WPA, drop to 0 remaining | Gain nothing, drop to 0 remaining |
| Any | Save | Carry forward to next state | — |

### Backward DP Recurrence
Define:
- **V₁[t]** = expected future WPA from optimally using **1** remaining challenge from time `t` onward
- **V₂[t]** = expected future WPA from optimally using **2** remaining challenges from time `t` onward

**Terminal condition** (end of game):

$$V_1[T] = 0, \quad V_2[T] = 0$$

**Recurrence** (for each timestep `t`, iterating backward):

$$V_1[t] = \max\Big(V_1[t{+}1], \;\max_{i \in \text{challenges}_t}\; c_i \cdot \text{wpa}_i\Big)$$

$$V_2[t] = \max\Big(V_2[t{+}1], \;\max_{i \in \text{challenges}_t}\; c_i \cdot \big(\text{wpa}_i + V_1[t{+}1]\big)\Big)$$

Where:
- $c_i$ is the confidence of overturning challenge $i$
- $\text{wpa}_i$ is the win probability added if challenge $i$ is successfully overturned
- The first term in each $\max$ represents **saving** (carrying the challenge forward)
- The second term represents **using** the best available challenge

The V₂ formula captures the key insight: winning a challenge when you have 2 remaining nets the immediate WPA **plus** the future option value of the retained challenge (V₁[t+1]).

### Outputs
After the backward pass, every `GameState` has two populated fields:

| Field | Meaning |
|---|---|
| `value_save_1` | Expected future WPA from having 1 challenge at this point, under optimal play |
| `value_save_2` | Expected future WPA from having 2 challenges at this point, under optimal play |

These values represent the **opportunity cost** of using a challenge: if a current challenge opportunity has expected value less than the save value, the optimal policy is to hold.

---

## Challenge Distributions

During each 15-second timestep, the simulation samples challengeable calls from three independent distributions: **Out-of-Bounds (OOB)**, **Foul**, and **Goaltending**. Each distribution captures both the frequency of calls and the confidence with which they can be overturned.

### Concepts

Each challenge type uses two key components:

1. **Call Categories** — The referee's call quality is modeled across three outcome tiers:
   - **Clear Correct**: Ref got it right (low overturn probability)
   - **Ambiguous**: Borderline call (medium overturn probability)
   - **Clear Incorrect**: Ref blew it (high overturn probability)

2. **Confidence Distributions** — For each category, a Beta distribution models the team's estimated overturn probability:
   - Lower β values (e.g., `beta(a=1, b=40)`) → concentrated near 0 (hard to overturn)
   - Higher α values (e.g., `beta(a=40, b=1)`) → concentrated near 1 (easy to overturn)
   - Equal α and β (e.g., `beta(a=5, b=4)`) → near-uniform spread

---

## Data Dependencies

| File | Format | Purpose |
|---|---|---|
| `data/markov_weights_*.parquet` | Parquet | Precomputed state transition probabilities (see `MARKOV_WEIGHTS_BUILD_GUIDE.md`) |
| `data/wpa_challenge_values.json` | JSON | WPA lookup by `(spread, time, margin, challenge_type)` (see `JSON_WPA_EXPORT_GUIDE.md`) |

---

## Simplifying Assumptions & Design Decisions

1. **Fixed 15-second timestep**: Challenges are evaluated at the same granularity as simulation steps. Challengeable calls are Poisson-sampled per timestep, so multiple calls per window are possible but rare.

2. **Score margin clipping**: Margins beyond ±20 are clipped before Markov lookup, since extreme blowouts have sparse training data and similar transition dynamics.

3. **Independent challenge valuation**: The DP treats each challenge independently within a timestep — it does not model using two challenges on two different calls in the same 15-second window. With small Poisson λ this scenario is negligible.

4. **Strict WPA lookups**: The `lookup_wpa()` function retrieves WPA values from the JSON without silent fallbacks. Missing `(spread, time, margin, type)` combinations will raise a `KeyError`, ensuring data completeness is verified and bugs surface immediately.
