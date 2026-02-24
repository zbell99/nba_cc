import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import concurrent.futures
from tqdm import tqdm

from DOCUMENTATION.DATA_DICTIONARIES.MARKOV_WEIGHTS_DATA_DICTIONARY import MARKOV_WEIGHTS_DATA_DICTIONARY as MW


#-- Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MARKOV_WEIGHTS_PATH = PROJECT_ROOT / "data" / "markov_weights_120_5_2.5_2760.0.parquet"


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


class GameSimulation:
    def __init__(self, time_elapsed, score_margin, home_team_spread, markov_weights: MarkovWeights):
        self.mw = markov_weights
        self.spread = self._align_spread_with_state(home_team_spread)
        self.states = [GameState(time_elapsed, score_margin)]
        self.time_per_step = 15  # seconds per simulation step, can be adjusted based on how granular we want the simulation to be


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
            next_state = self._sample_next_state(self.states[-1])
            if next_state is None:
                break  # no more transitions available
            self.states.append(next_state)
        return self.states[-1]  # return final state at end of simulation
    

    def _sample_next_state(self, current_state: GameState) -> GameState:
        clipped_score_margin = max(min(current_state.score_margin, 20), -20)  # clip to range of score margins in Markov weights
        state_row = {
            MW.TIME_ELAPSED.value: self._align_time_with_state(current_state.time_elapsed),
            MW.SCORE_MARGIN.value: self._align_score_margin_with_state(clipped_score_margin),
            MW.HOME_TEAM_SPREAD.value: self.spread,
        }

        # Find the row in markov_weights that matches the current state - only return the columns p-5 to p+5 for the probabilities of next score margin changes
        weight_distribution: list = state_weight_distribution(state_row, self.mw.markov_weights)
        if weight_distribution is None:
            raise ValueError(f"No Markov weights found for state {state_row}. Cannot sample next state.")
        

        # Sample the next score_margin based on the probabilities in that row
        score_margin_changes = np.arange(-5, 6)  # possible score margin changes from -5 to +5
        next_score_margin_change = int(np.random.choice(score_margin_changes, p=weight_distribution))
        next_score_margin = current_state.score_margin + next_score_margin_change

        return GameState(
            time_elapsed=current_state.time_elapsed + self.time_per_step,  # assuming we sample every 15 seconds
            score_margin=next_score_margin
        )


def read_markov_weights(path: Path) -> pd.DataFrame:
    """Read precomputed Markov weights from Parquet."""
    return pd.read_parquet(path)


def state_weight_distribution(state, markov_weights: pd.DataFrame) -> pd.DataFrame:
    weight_distribution = markov_weights[
        (markov_weights[MW.TIME_ELAPSED.value] == state[MW.TIME_ELAPSED.value]) &
        (markov_weights[MW.SCORE_MARGIN.value] == state[MW.SCORE_MARGIN.value]) &
        (markov_weights[MW.HOME_TEAM_SPREAD.value] == state[MW.HOME_TEAM_SPREAD.value])
    ].iloc[:, markov_weights.columns.get_loc(MW.AWAY5.value):markov_weights.columns.get_loc(MW.HOME5.value)+1]
    
    if weight_distribution.empty:
        print(f"Warning: No Markov weights found for state {state}. Ending simulation.")
        return None
    
    return weight_distribution.values.flatten().tolist()


def _game(initial_time, initial_score_margin, initial_spread, mw):
    simulation = GameSimulation(initial_time, initial_score_margin, initial_spread, mw)
    final_state = simulation.simulate_game()
    return final_state.score_margin


def main():
    print("Loading Markov weights...")
    markov_weights = read_markov_weights(MARKOV_WEIGHTS_PATH)
    mw = MarkovWeights(markov_weights, time_gap=120, score_gap=2, odds_gap=2.0)
    print(f"  {len(markov_weights):,} states with Markov weights")

    # Example usage: simulate a game starting at 0 seconds and 0 score margin with a pregame spread of -3.5
    initial_time = 1440.0
    initial_score_margin = 0
    initial_spread = 15.0

    print(f"Simulating game with initial state: time_elapsed={initial_time}, score_margin={initial_score_margin}, home_team_spread={initial_spread} ...")
    games = []

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [
            executor.submit(_game, initial_time, initial_score_margin, initial_spread, mw)
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
