import pandas as pd
import numpy as np
from pathlib import Path
import concurrent.futures
from tqdm import tqdm

from DOCUMENTATION.DATA_DICTIONARIES.NBA_SNAPSHOT_DATA_DICTIONARY import NBA_SNAPSHOT_DATA_DICTIONARY as NSD

#TODO: decisions to later justify:
# - which variables to include in the state definition (data for possession of ball?)
# - padding of the decision points (e.g., time_elapsed in 15 second intervals, score_diff in 2 point intervals, etc
# - how to handle end-of-game states where there may be few transitions (e.g., do we include all states up to the final buzzer, or do we exclude states after a certain time cutoff like 2760 seconds which is 46 minutes to exclude the last few minutes of close games that may not have meaningful transitions)
# - how many states we end up with and how to balance granularity of states with having enough samples to compute meaningful transition probabilities (e.g., if we have too many states with very specific time_elapsed, score_diff, and spread values, we may not have enough samples in each state to compute reliable probabilities, but if we have too few states with very wide padding, we may lose important distinctions between different game situations)
# - visualization of the resulting Markov weights (e.g., how to show the distribution of next states for a given current state in a way that's easy to understand and actionable for decision making) - are there combos of state that have similar transition probabilities that we could cluster together for a lighter model?



# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GAME_STATE_PATH = PROJECT_ROOT / "data" / "nba_snapshot_data.parquet"


def game_state_data() -> pd.DataFrame:
    """Load preprocessed game state data."""
    return pd.read_parquet(GAME_STATE_PATH)


def pivot_game_state_data(
    df: pd.DataFrame,
    time_gap: int = 15, #must be a multiple of 15 to match snapshot intervals
    time_padding: int = 0,
    score_padding: int = 0,
    odds_padding: float = 0.5,
    time_cutoff: float = 2880 # first 48 minutes (2880 seconds) to exclude end-of-game states with few transitions
) -> pd.DataFrame:
    """
    Pivot the game state data to create Markov weight distributions.
    
    At each game state, we want to know the distribution of next states, which we can use as transition probabilities in a Markov model. To do this, we will create "padded" versions of the time_elapsed, score_diff, and home_team_spread columns to define discrete game states.

    The padding parameters control how we bucket the continuous variables:
    - time_padding: padding size for time_elapsed (e.g., our transition probabilities for a state at 300 seconds would be derived from all states with time_elapsed in [285, 315] if time_padding is 15)
    - score_padding: padding size for score_diff (e.g., our transition probabilities for a 5 point lead would be derived from all states with score_diff in [5 - score_padding, 5 + score_padding])
    - odds_padding: padding size for home_team_spread (e.g., if the spread is -3.5, we might include all states with spread in [-4.0, -3.0] if odds_padding is 0.5)
    - time_cutoff: maximum time_elapsed to include in the output (to exclude end of game states that may not have meaningful transitions)

    The function will return a DataFrame where each row corresponds to a unique game state and includes the distribution of next states (the "weights" for the Markov model) based on the padded variables.
    The df should have the following columns:
    - time_elapsed: the elapsed time in seconds
    - score_diff: the score difference (home_score - away_score)
    - home_team_spread: the betting spread for the home team
    - sample_size: the number of samples (next states) that were used to compute the distribution for this state
    - p-5: the probability of the next state having score_diff 5+ less than current state
    - p-4: the probability of the next state having score_diff 4 less than current state
    - p-3: the probability of the next state having score_diff 3 less than current state
    - p-2: the probability of the next state having score_diff 2 less than current state
    - p-1: the probability of the next state having score_diff 1 less than current state
    - p+0: the probability of the next state having same score_diff as current state
    - p+1: the probability of the next state having score_diff 1 greater than current state
    - p+2: the probability of the next state having score_diff 2 greater than current state
    - p+3: the probability of the next state having score_diff 3 greater than current state
    - p+4: the probability of the next state having score_diff 4 greater than current state
    - p+5: the probability of the next state having score_diff 5+ greater than current state
    """
    # Prep data
    df = df.sort_values([
        NSD.GAME_ID,
        NSD.TIME_ELAPSED
    ]).reset_index(drop=True)

    # only have states every time_gap seconds to reduce number of states and ensure we have enough samples in each state to compute probabilities (e.g., if time_gap is 15, we only keep states at 0s, 15s, 30s, etc)
    df = df[df[NSD.TIME_ELAPSED] % time_gap == 0].copy()

    # Compute next state's score_diff within each game
    df["next_score_margin"] = df.groupby(NSD.GAME_ID)[NSD.SCORE_MARGIN].shift(-1)

    # Filter to only include states within the time cutoff
    df = df[df[NSD.TIME_ELAPSED] <= time_cutoff].copy()

    # Remove rows without a next state (last snapshot of each game has no transition)
    df = df.dropna(subset=["next_score_margin"])

    # Compute score change to next state and clip to [-5, 5]
    df["score_change"] = (df["next_score_margin"] - df[NSD.SCORE_MARGIN]).clip(-5, 5).astype(int)

    # Get unique states we want to compute probabilities for
    score_states = np.arange(-20, 21)
    spread_states = np.arange(-15.5, 15.5, 1.0) # example spread states from -15.5 to +15.5 in 2 point increments
    time_states = np.arange(0, time_cutoff + 45, 45) # example time states every 45 seconds
    states = [{
        NSD.TIME_ELAPSED: t,
        NSD.SCORE_MARGIN: s,
        NSD.HOME_TEAM_SPREAD: sp
    } for t in time_states for s in score_states for sp in spread_states]

    
    # Build result rows using vectorized filtering for each state
    results = []
    
    # Parallel processing
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(_compute_state_row, state_row, df, time_padding, score_padding, odds_padding)
            for state_row in states
        ]
        for f in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Computing Markov weights"):
            results.append(f.result())
    
    return pd.DataFrame(results)


def _compute_state_row(state_row, df, time_padding, score_padding, odds_padding):
    current_time = state_row[NSD.TIME_ELAPSED]
    current_score = state_row[NSD.SCORE_MARGIN]
    current_spread = state_row[NSD.HOME_TEAM_SPREAD]

    mask = (
        (df[NSD.TIME_ELAPSED] >= current_time - time_padding) &
        (df[NSD.TIME_ELAPSED] <= current_time + time_padding) &
        (df[NSD.SCORE_MARGIN] >= current_score - score_padding) &
        (df[NSD.SCORE_MARGIN] <= current_score + score_padding) &
        (df[NSD.HOME_TEAM_SPREAD] >= current_spread - odds_padding) &
        (df[NSD.HOME_TEAM_SPREAD] <= current_spread + odds_padding)
    )

    matching_rows = df[mask]
    sample_size = len(matching_rows)

    row_data = {
        NSD.TIME_ELAPSED: current_time,
        NSD.SCORE_MARGIN: current_score,
        NSD.HOME_TEAM_SPREAD: current_spread,
        "sample_size": sample_size,
    }

    for bucket_val in range(-5, 6):
        if bucket_val < 0:
            bucket_name = f"p{bucket_val}"
        else:
            bucket_name = f"p+{bucket_val}"

        count = (matching_rows["score_change"] == bucket_val).sum()
        row_data[bucket_name] = count / sample_size if sample_size > 0 else 0.0

    return row_data


def main():
    print("Loading game state data...")
    df = game_state_data()
    print(f"  {len(df):,} snapshot rows")

    print("Pivoting to Markov weights...")
    time_gap = 45 #seconds
    time_padding = 120 #seconds
    score_padding = 5 #points
    odds_padding = 2.5 #points
    time_cutoff = 2880.0 #seconds
    weights_df = pivot_game_state_data(df, time_gap=time_gap, time_padding=time_padding, score_padding=score_padding, odds_padding=odds_padding, time_cutoff=time_cutoff)
    print(f"  {len(weights_df):,} unique states with weights")

    # example of what the output looks like (all columns)
    for col in weights_df.columns:
        print(col + ": ", end="")
        print(weights_df[col].iloc[0])

    print(f"Saving to {PROJECT_ROOT / 'data' / 'markov_weights.parquet'} ...")
    weights_df.to_parquet(PROJECT_ROOT / "data" / f"markov_weights_v2.parquet", index=False)


if __name__ == "__main__":
    main()
