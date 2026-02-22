# import pbpstats
from sportsdataverse.nba.nba_loaders import load_nba_pbp

def download_nba_pbp(seasons=[], return_as_pandas=False):
    """Load NBA play-by-play data"""
    df = load_nba_pbp(seasons=range(2020,2026), return_as_pandas=True)
    df.to_csv("nba_pbp_data.csv", index=False)
