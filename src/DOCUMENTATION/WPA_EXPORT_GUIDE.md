# WPA Challenge Values Export Implementation Guide

## Overview
This document outlines the implementation of a Parquet-based data export for efficient WPA (Win Probability Added) challenge value access by game state.

## Project Goals
Create an efficient, queryable Parquet file that enables fast lookups and filtering of WPA values for different challenge types based on three game state parameters:
- **Line**: Pregame betting line (fixed)
- **GT**: Game time in seconds (0-2880 for a full game)
- **M**: Score margin (in points)

## Final Structure

Tabular format with the following columns:
```
gt      line    m    oob_challenge  nofoul2_keepBall  nofoul2_jumpBall  ...
100     0       -5   -0.0234        0.0156            0.0089            ...
100     0       -4   -0.0198        0.0172            0.0101            ...
100     0       -3   -0.0167        0.0185            0.0112            ...
...
```

All combinations of:
- **GT**: values that exist in source data
- **Line**: -15 to 15 (complete range, interpolated where needed)
- **M**: -20 to 20 (complete range, interpolated where needed)
- **Challenge metrics**: oob_challenge, nofoul2_keepBall, nofoul2_jumpBall, nofoul2_loseBall, nofoul3_keepBall, nofoul3_jumpBall, nofoul3_loseBall, nogoaltend, noand1


## Implementation Details

### Data Processing Pipeline
1. **Load raw data** from RData file and deduplicate on (gt, m, line)
2. **Early interpolation** on base columns (H_P, A_P, H_M1, A_FT1, H_M2, A_FT2, A_FT3) to create complete (gt, line, m) grid where line ∈ [-15, 15] and m ∈ [-20, 20]
   - This ensures all lag columns and downstream calculations have complete data
3. **Create df_enhanced** with lag columns (H_M2, A_FT1_M2) built on interpolated data
4. **Calculate challenge values** as differentials of win probabilities
5. **Export to Parquet** for efficient downstream access

### Interpolation Strategy
- **Timing**: Happens immediately after deduplication, before df_enhanced creation
- **Grid**: Full cartesian product of (gt from data, line [-15 to 15], m [-20 to 20])
- **Method**: Linear weighted interpolation based on distance to nearest non-NA values
  - First pass: interpolate across m within each (gt, line) pair
  - Second pass: interpolate across line within each (gt, m) pair
- **Result**: Complete, continuous data for all game states

### Challenge Types Included
- `oob_challenge`: Out of bounds challenge
- `nofoul2_keepBall`: Foul but keeps ball
- `nofoul2_jumpBall`: Foul but jump ball results
- `nofoul2_loseBall`: Foul but loses ball
- `nofoul3_keepBall`: 3-point foul, keeps ball
- `nofoul3_jumpBall`: 3-point foul, jump ball
- `nofoul3_loseBall`: 3-point foul, loses ball
- `nogoaltend`: Goaltend call overturned
- `noand1`: And-1 foul overturned

## Key Technical Learnings

### 1. Early Interpolation Enables Complete Data
**Problem**: Interpolating after df_enhanced creation resulted in NAs because lag columns depended on non-existent records.

**Solution**: Interpolate base columns (H_P, A_P, etc.) immediately after deduplication, before creating df_enhanced.
- Creates complete grid of (gt, line ∈ [-15, 15], m ∈ [-20, 20])
- All downstream lag columns and calculations work with continuous data
- Challenge values are fully populated when exported

**Impact**: Eliminates NAs in final output and ensures simulation/API have complete game state coverage.

### 2. Parquet vs JSON for Downstream Access
**Parquet advantages over JSON for this use case:**
- **Speed**: Binary columnar format is faster to read than text JSON
- **Filtering**: Can selectively load subsets (e.g., all rows where line=0 and m=5)
- **Size**: Compression reduces file size vs nested JSON structure
- **Integration**: Native support in pandas (Python) for simulation and FastAPI
- **Memory**: Can load entire table once at startup for fast synchronous lookups

**Python Access Pattern:**
```python
import pandas as pd

# In simulation: query specific game states
wpa_data = pd.read_parquet("data/wpa_challenge_values.parquet")
row = wpa_data[(wpa_data.line == 0) & (wpa_data.gt == 100) & (wpa_data.m == 3)]

# In FastAPI: load once at startup
@app.on_event("startup")
async def startup():
    app.wpa_data = pd.read_parquet("data/wpa_challenge_values.parquet")
```

### 3. Interpolation Function Design
The `interpolate_vec()` function:
- Handles empty vectors explicitly (avoids warnings from max/min on empty results)
- Uses `length()` checks to safely determine before/after neighbors
- Applies weighted average for consecutive missing values: `(x_left * dist_right + x_right * dist_left) / (dist_left + dist_right)`
- Falls back to nearest available value if no data on one side
- Preserves any remaining NAs (boundary cases)

#\

## Design Decisions

### Why Early Interpolation?
- **Ensures complete data**: Lag columns (H_M2, A_FT1_M2) depend on lookups that may not exist without interpolation
- **Single computation**: Interpolate once before df_enhanced creation, not separately for each gt
- **Consistency**: All downstream analysis, visualizations, and exports work with the same complete dataset
- **Clarity**: Transformation pipeline is more linear and easier to understand

### Why Parquet Over JSON?
**Parquet benefits:**
1. **Read Performance**: Binary columnar format is significantly faster than parsing JSON text
2. **Filtering Efficiency**: Can load only relevant rows (e.g., specific line and m values)
3. **Compression**: Typically 30-50% smaller than equivalent JSON
4. **Python Integration**: Native pandas support for both simulation and FastAPI
5. **Memory**: Load table once at startup in FastAPI for O(1) row lookups

**Use case fit:**
- Simulation: Repeatedly queries specific game states → Parquet filtering is ideal
- FastAPI: Synchronous lookups need fast access → Load once in memory, query instantly
- Both prefer tabular format over nested structure

### Data Completeness Guarantee
The complete (gt, line ∈ [-15, 15], m ∈ [-20, 20]) grid ensures:
- No missing game states in simulation
- API always has values to return
- Billing line ranges from standard -20 to +20
- Game margins from -20 to +20 cover realistic scenarios

## Performance Characteristics

### Parquet Storage
- **File size**: Compressed columnar format, ~30-50% smaller than JSON
- **Read time**: Binary format is 5-10x faster to read than JSON
- **Memory**: Load entire table at startup (< 100MB typical), then O(1) row lookups via filtering

### Access Patterns
- **Simulation**: Filter by (gt, line, m) → Returns row with all challenge values
- **FastAPI**: Query parameters (line, gt, m) → Direct DataFrame row selection → JSON response
- **Lookup time**: O(1) after initial load

## Next Steps

### Integration Points
1. **Simulation** (`nba_game_sim.py`):
   - Load Parquet at startup: `wpa_data = pd.read_parquet("data/wpa_challenge_values.parquet")`
   - Query game state: `row = wpa_data[(wpa_data.line==X) & (wpa_data.gt==Y) & (wpa_data.m==Z)]`
   - Extract challenge values for decision logic

2. **FastAPI** (`main.py`):
   - Load at startup in event handler
   - Expose `/wpa/{line}/{gt}/{m}` endpoint
   - Return matching row as JSON response
   - Synchronous queries for real-time decision support

3. **Caching** (optional):
   - Load entire Parquet in memory once
   - Query via filtered DataFrame (no re-reads)
   - Cache results if repeated queries common

## References
- [data_exploration.Rmd](../data_exploration.Rmd) - Data processing and export pipeline
- [CODING_STANDARDS_R.md](CODING_STANDARDS_R.md) - Project coding conventions
- Output file: `data/wpa_challenge_values.parquet`
