# read sim challenge values and display as heatmap
# spread 0, oob challenge, score margin on y axis, time on x axis, color = wpa/ev1 (clipped to 100%)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def plot_heatmap(data):
    data = data.copy()
    data['api_value'] = (data['ev1'] / data["noand1"]) * 100
    data['api_value'] = data['api_value'].clip(upper=100, lower=0)

    # Pivot the data to create a matrix for the heatmap
    heatmap_data = data.pivot(index='m', columns='gt', values='api_value')
    
    # Create the heatmap
    plt.figure(figsize=(12, 8))
    sns.heatmap(heatmap_data, fmt=".1f", cmap="YlGnBu", cbar_kws={'label': 'Breakeven Confidence (%)'})
    
    x_ticks = heatmap_data.columns
    for tick in x_ticks:
        if tick % 720 == 0 and tick < 2880 and tick != x_ticks[0]:
            plt.axvline(x=list(x_ticks).index(tick), color='red', linewidth=2)


    # Set labels and title
    plt.title('Breakeven Confidence - No And1 Challenge (Spread = 0)')
    plt.xlabel('Time Elapsed (seconds)')
    plt.ylabel('Score Margin')
    
    # Show the plot
    plt.show()

def main():
    # Load the data from the parquet file
    data = pd.read_parquet("data/wpa_challenge_values_sim.parquet")
    
    # Filter for spread = 0 and oob challenge type
    filtered_data = data[(data['line'] == 0)]
    
    # Plot the heatmap
    plot_heatmap(filtered_data)

if __name__ == "__main__":
    main()
