import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import concurrent.futures
from tqdm import tqdm

from DOCUMENTATION.DATA_DICTIONARIES.MARKOV_WEIGHTS_DATA_DICTIONARY import MARKOV_WEIGHTS_DATA_DICTIONARY as MW
from DOCUMENTATION.DATA_DICTIONARIES.CHALLENGE_DISTRIBUTIONS import (
    OOBChallenge as OOB,
    FoulChallenge as Foul,
    GoaltendChallenge as GT,
    ChallengeType as CT
)


#-- Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MARKOV_WEIGHTS_PATH = PROJECT_ROOT / "data" / "markov_weights_120_5_2.5_2760.0.parquet"
WPA_DATA_PATH = PROJECT_ROOT / "data" / "wpa_challenge_values.parquet"


class MarkovWeights:
    def __init__(self, markov_weights: pd.DataFrame, time_gap: int = 120, score_gap: int = 2, odds_gap: float = 2.0):
        self.markov_weights = markov_weights
        self.time_gap = time_gap
        self.score_gap = score_gap
        self.odds_gap = odds_gap


class GameState:
    def __init__(self, time_elapsed, score_margin):
        self.time_elapsed = time_elapsed
        self.score_margin = score_margin
        self.challenges = []    # list[Challenge] — challengeable calls at this state
        self.value_save_1 = 0.0 # expected future WPA from optimally using 1 remaining challenge
        self.value_save_2 = 0.0 # expected future WPA from optimally using 2 remaining challenges


class ChallengeableCall:
    """A challengeable call occurring at a particular game state."""
    def __init__(self, challenge_type: CT, confidence: float):
        self.type = challenge_type        # e.g. 'nofoul2_keepBall', 'oob_challenge'
        self.confidence = confidence      # probability of successful overturn (0-1)
        


class GameSimulation:
    def __init__(self, time_elapsed, score_margin, home_team_spread, markov_weights: MarkovWeights, time_per_step=15):
        self.mw = markov_weights
        self.spread = self._align_spread_with_state(home_team_spread)
        self.states = [GameState(time_elapsed, score_margin)]
        self.time_per_step = time_per_step  # seconds per simulation step, can be adjusted based on how granular we want the simulation to be
        self.oob_challenge = OOB(min_per_time_period=self.time_per_step/60)
        self.foul_challenge = Foul(min_per_time_period=self.time_per_step/60)
        self.goaltend_challenge = GT(min_per_time_period=self.time_per_step/60)


    def _align_spread_with_state(self, initial_spread):
        n = round((initial_spread - 0.5) / self.mw.odds_gap)
        aligned_spread = 0.5 + n * self.mw.odds_gap
        return aligned_spread
    

    def _align_score_margin_with_state(self, score_margin):
        n = round(score_margin / self.mw.score_gap)
        aligned_score_margin = n * self.mw.score_gap
        return aligned_score_margin
    

    def _align_time_with_state(self, time_elapsed):
        n = round(time_elapsed / self.mw.time_gap)
        aligned_time = n * self.mw.time_gap
        return aligned_time

        

    def simulate_game(self, time_cutoff: float=2760):
        while self.states[-1].time_elapsed < time_cutoff:
            next_state = self.sample_next_state(self.states[-1])

            if next_state is None:
                break  # no more transitions available
            self.states.append(next_state)
        return self.states  # return list of states at end of simulation
    

    def sample_next_state(self, current_state: GameState) -> GameState:

        clipped_score_margin = max(min(current_state.score_margin, 20), -20)  # clip to range of score margins in Markov weights
        state_row = {
            MW.TIME_ELAPSED: self._align_time_with_state(current_state.time_elapsed),
            MW.SCORE_MARGIN: self._align_score_margin_with_state(clipped_score_margin),
            MW.HOME_TEAM_SPREAD: self.spread,
        }

        # Find the row in markov_weights that matches the current state - only return the columns p-5 to p+5 for the probabilities of next score margin changes
        weight_distribution: list = state_weight_distribution(state_row, self.mw.markov_weights)
        if weight_distribution is None:
            raise ValueError(f"No Markov weights found for state {state_row}. Cannot sample next state.")
        

        # Sample the next score_margin based on the probabilities in that row
        score_margin_changes = np.arange(-5, 6)  # possible score margin changes from -5 to +5
        next_score_margin_change = int(np.random.choice(score_margin_changes, p=weight_distribution))
        next_score_margin = current_state.score_margin + next_score_margin_change

        # Sample challenges according to the imported distributions
        # for each challenge type, we first sample how many challenges of that type occur in this time step (e.g., from a Poisson distribution), then for each challenge we sample whether it's clear correct, ambiguous, or clear incorrect, and then we sample the confidence of the challenge based on the corresponding Beta distribution for that category. We add all sampled challenges to the next state.
        oob_challenges = sample_challenges(self.oob_challenge)
        foul_challenges = sample_challenges(self.foul_challenge)
        gt_challenges = sample_challenges(self.goaltend_challenge)

        current_state.challenges.extend(oob_challenges)
        current_state.challenges.extend(foul_challenges)
        current_state.challenges.extend(gt_challenges)

        return GameState(
            time_elapsed=current_state.time_elapsed + self.time_per_step,  # assuming we sample every 15 seconds
            score_margin=next_score_margin
        )


def read_markov_weights(path: Path) -> pd.DataFrame:
    """Read precomputed Markov weights from Parquet."""
    return pd.read_parquet(path)


def state_weight_distribution(state, markov_weights: pd.DataFrame) -> pd.DataFrame:
    weight_distribution = markov_weights[
        (markov_weights[MW.TIME_ELAPSED] == state[MW.TIME_ELAPSED]) &
        (markov_weights[MW.SCORE_MARGIN] == state[MW.SCORE_MARGIN]) &
        (markov_weights[MW.HOME_TEAM_SPREAD] == state[MW.HOME_TEAM_SPREAD])
    ].iloc[:, markov_weights.columns.get_loc(MW.AWAY5):markov_weights.columns.get_loc(MW.HOME5)+1]
    
    if weight_distribution.empty:
        print(f"Warning: No Markov weights found for state {state}. Ending simulation.")
        return None
    
    return weight_distribution.values.flatten().tolist()


def sample_challenges(challenge):
    num_challenges = challenge.distribution.rvs()  # sample number of challenges occurring in this time step
    sampled_challenges = []
    for _ in range(num_challenges):
        # ------ Sample challenge type ------
        challenge_types = [call.challenge_type for call in challenge.call_types]
        p_values = [call.p for call in challenge.call_types]
        idx = np.random.choice(len(challenge_types), p=p_values)
        challenge_type = challenge_types[idx]
        if challenge_type is CT.ALREADY_IN_YOUR_FAVOR:
            continue  # skip if no challenge occurs (e.g., for the "Called in your favor, no need to challenge")
        
        # ------ Sample challenge category (clear correct, ambiguous, clear incorrect) ------
        category_names = list(vars(challenge.call_categories).keys())
        category_probs = [getattr(challenge.call_categories, name) for name in category_names]
        category = np.random.choice(category_names, p=category_probs)
        
        # ------ Sample challenge confidence from the corresponding Beta distribution for the sampled category ------
        category_confidence_dist = getattr(challenge.call_confidences, category)
        confidence = category_confidence_dist.rvs()  # sample confidence from the corresponding Beta distribution

        sampled_challenges.append(ChallengeableCall(challenge_type=challenge_type, confidence=confidence))

    return sampled_challenges


def load_wpa_data(path: Path = WPA_DATA_PATH) -> pd.DataFrame:
    """Load the WPA challenge values Parquet lookup table."""
    return pd.read_parquet(path)


def lookup_wpa(wpa_data: pd.DataFrame, spread: float, time_elapsed: float,
               score_margin: float, challenge_type: CT) -> float:
    """Look up WPA value for a challenge type at a given game state.
    """

    clipped_score_margin = max(min(score_margin, 20), -20)  # clip to range of score margins in WPA data
    clipped_line = max(min(spread, 15), -15)  # clip to range of lines in WPA data



    row = wpa_data[(wpa_data['line'] == clipped_line) & (wpa_data['gt'] == time_elapsed) & (wpa_data['m'] == clipped_score_margin)]

    if len(row) == 0:
        raise ValueError(f"No WPA data found for line={clipped_line}, gt={time_elapsed}, m={clipped_score_margin}")

    return float(row[challenge_type].iloc[0])


def derive_challenge_value(
    states: list[GameState],
    wpa_data: pd.DataFrame,
    spread: float,
) -> list[GameState]:
    """Backward DP to compute the value of having 1 or 2 challenges at each state.

    Populates *value_save_1* and *value_save_2* on every GameState:
      - value_save_1: expected future WPA from optimally using 1 remaining challenge
      - value_save_2: expected future WPA from optimally using 2 remaining challenges

    NBA coach's challenge transition rules:
      - 2 remaining + WIN  → 1 remaining  (gain WPA + future value of having 1)
      - 2 remaining + LOSE → 0 remaining  (gain nothing)
      - 1 remaining + WIN  → 0 remaining  (gain WPA)
      - 1 remaining + LOSE → 0 remaining  (gain nothing)
    """
    n = len(states)
    if n == 0:
        return states

    # Terminal state — no future value
    states[-1].value_save_1 = 0.0
    states[-1].value_save_2 = 0.0

    # ---------- backward pass ----------
    for t in range(n - 2, -1, -1):
        state = states[t]
        next_v1 = states[t + 1].value_save_1
        next_v2 = states[t + 1].value_save_2

        best_use_1 = 0.0  # best EV from using the challenge with 1 remaining
        best_use_2 = 0.0  # best EV from using the challenge with 2 remaining

        for challenge in state.challenges:
            challenge: ChallengeableCall
            
            wpa = lookup_wpa(
                wpa_data,
                spread,
                state.time_elapsed,
                state.score_margin,
                challenge.type,
            )

            # --- 1 remaining: use → 0 regardless of outcome ---
            # EV = P(win) × wpa
            ev_use_1 = challenge.confidence * wpa
            best_use_1 = max(best_use_1, ev_use_1)

            # --- 2 remaining: WIN → wpa + have 1 left, LOSE → 0 ---
            # EV = P(win) × (wpa + V1[t+1])
            ev_use_2 = challenge.confidence * (wpa + next_v1)
            best_use_2 = max(best_use_2, ev_use_2)

        # Optimal policy: save (carry forward) vs. use best available
        state.value_save_1 = max(next_v1, best_use_1)
        state.value_save_2 = max(next_v2, best_use_2)

    return states


def _game_with_challenges(initial_time, initial_score_margin, initial_spread, mw, wpa_data):
    simulation = GameSimulation(initial_time, initial_score_margin, initial_spread, mw, time_per_step=15)
    states = simulation.simulate_game()
    states = derive_challenge_value(states, wpa_data, initial_spread)
    final_state = states[-1]
    return final_state.score_margin


def main():
    print("Loading Markov weights...")
    markov_weights = read_markov_weights(MARKOV_WEIGHTS_PATH)
    mw = MarkovWeights(markov_weights, time_gap=120, score_gap=2, odds_gap=2.0)
    print(f"  {len(markov_weights):,} states with Markov weights")

    print("Loading WPA challenge values...")
    wpa_data = load_wpa_data(WPA_DATA_PATH)
    print("  WPA data loaded")

    # Example usage: simulate a game starting at 0 seconds and 0 score margin with a pregame spread of -3.5
    initial_time = 0.0
    initial_score_margin = 0
    initial_spread = 2.0

    print(f"Simulating game with initial state: time_elapsed={initial_time}, score_margin={initial_score_margin}, home_team_spread={initial_spread} ...")
    games = []

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(_game_with_challenges, initial_time, initial_score_margin, initial_spread, mw, wpa_data)
            for i in range(1000)
        ]
        for f in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc=f"Running Game Simulation for Spread {initial_spread}"):
            games.append(f.result())
    
    # Example output: distribution of final score margins after simulating 1000 games
    print("Histogram of final score margins after simulating 1000 games:")
    plt.hist(games, bins='auto', density=True)
    plt.xlabel('Margin')
    plt.ylabel(r'% of Simulated Games')
    plt.title(f'Scores for Simulated Games - Spread {initial_spread}')
    plt.show()

if __name__ == "__main__":
    main()
