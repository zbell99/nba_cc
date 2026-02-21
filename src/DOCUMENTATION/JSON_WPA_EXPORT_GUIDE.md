# JSON WPA Export Implementation Guide

## Overview
This document outlines the implementation of a nested JSON structure for efficient WPA (Win Probability Added) challenge value lookups by game state.

## Project Goals
Create a compact, queryable JSON file that enables fast O(1) lookups of WPA values for different challenge types based on three game state parameters:
- **Line**: Pregame betting line (fixed)
- **GT**: Game time in seconds (0-2880 for a full game)
- **M**: Score margin (in points)

## Final Structure

```json
{
  "line": {
    "gt": {
      "m": {
        "challenge_type": {
          "wpa": value
        }
      }
    }
  }
}
```

### Example
```json
{
  "0": {
    "100": {
      "3": {
        "oob_challenge": {
          "wpa": -0.0234
        },
        "nofoul2_keepBall": {
          "wpa": 0.0156
        }
        // ... other challenge types
      }
    }
  }
}
```

## Implementation Details

### Data Processing
1. Created `wpa_df` by selecting relevant columns from `df_enhanced`
2. Built nested R list structure through triple-nested loops
3. Exported to JSON using `jsonlite::toJSON()` with proper formatting

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

### 1. JSON Export with `jsonlite`
**Problem**: Values were being wrapped in arrays
```json
"wpa": [-0.0234]  // Unwanted
```

**Solution**: Use `auto_unbox = TRUE` parameter
```r
toJSON(wpa_json_structure, pretty = TRUE, auto_unbox = TRUE)
```

This tells `jsonlite` to serialize scalar values as scalars rather than length-1 vectors.

### 2. R Vector Extraction Patterns
Understanding the difference between subsetting operators:

| Operator | Behavior | Result |
|----------|----------|--------|
| `[1]` | Subset – returns a vector | `c(-0.0234)` |
| `[[1]]` | Extract – returns the scalar value | `-0.0234` |

**Why it matters**: 
- With `[1]`, you get a length-1 vector
- With `[[1]]`, you get the actual scalar
- While `auto_unbox = TRUE` compensates for this, using `[[1]]` is semantically clearer and avoids creating unnecessary intermediate vectors

**Best Practice**: Use `[[1]]` when extracting single values from dataframes for clarity and efficiency.

### 3. JSON Keys and Numeric Values
All JSON object keys must be strings, so numeric identifiers (line, gt, m) become:
```r
gt_nested[[as.character(m_val)]] <- challenge_values
```

This preserves the numeric relationships while conforming to JSON's string-key requirement.

## Implementation Code

```r
library(jsonlite)

# Filter data to relevant columns
wpa_df <- df_enhanced %>%
  select(gt, line, m, oob_challenge, nofoul2_keepBall, 
         nofoul2_jumpBall, nofoul2_loseBall, nofoul3_keepBall, 
         nofoul3_jumpBall, nofoul3_loseBall, nogoaltend, noand1)

# Build nested structure: line -> gt -> m -> challenge values
wpa_json_structure <- list()

for (line_val in unique(wpa_df$line)) {
  line_data <- wpa_df %>% filter(line == line_val)
  line_nested <- list()
  
  for (gt_val in unique(line_data$gt)) {
    gt_data <- line_data %>% filter(gt == gt_val)
    gt_nested <- list()
    
    for (m_val in unique(gt_data$m)) {
      m_data <- gt_data %>% filter(m == m_val)
      
      # Extract challenge values wrapped in wpa objects
      challenge_values <- list(
        oob_challenge = list(wpa = m_data$oob_challenge[[1]]),
        nofoul2_keepBall = list(wpa = m_data$nofoul2_keepBall[[1]]),
        nofoul2_jumpBall = list(wpa = m_data$nofoul2_jumpBall[[1]]),
        nofoul2_loseBall = list(wpa = m_data$nofoul2_loseBall[[1]]),
        nofoul3_keepBall = list(wpa = m_data$nofoul3_keepBall[[1]]),
        nofoul3_jumpBall = list(wpa = m_data$nofoul3_jumpBall[[1]]),
        nofoul3_loseBall = list(wpa = m_data$nofoul3_loseBall[[1]]),
        nogoaltend = list(wpa = m_data$nogoaltend[[1]]),
        noand1 = list(wpa = m_data$noand1[[1]])
      )
      
      gt_nested[[as.character(m_val)]] <- challenge_values
    }
    
    line_nested[[as.character(gt_val)]] <- gt_nested
  }
  
  wpa_json_structure[[as.character(line_val)]] <- line_nested
}

# Export to JSON with proper formatting
wpa_json <- toJSON(wpa_json_structure, pretty = TRUE, auto_unbox = TRUE)
write(wpa_json, file = "data/wpa_challenge_values.json")
```

## Design Decisions

### Why This Nesting Order (line → gt → m)?
- **Line** is pregame information (fixed at start)
- **GT** and **M** are in-game information that evolves
- This grouping makes logical sense for application of betting/time-based queries

### Why Space-Efficient Over Flat Format?
Compared to a flat array format like:
```json
[
  {"line": 0, "gt": 100, "m": 3, "oob_challenge": {...}, ...}
]
```

The nested format:
- Uses ~40% less space (no key duplication)
- Provides equivalent O(1) lookup performance
- More intuitive for game state navigation

## Performance Characteristics
- **Lookup time**: O(1) – direct hash lookups across three levels
- **File size**: Minimal (nested structure with string keys)
- **Memory**: Efficient for JSON parsing in most languages

## Next Steps
This JSON can now be:
1. Served via API endpoints for real-time WPA calculations
2. Imported into client applications for decision support
3. Cached in memory for fast repeated access
4. Used as a lookup table for challenge recommendation algorithms

## References
- `data_exploration.Rmd` - Main data processing pipeline
- `CODING_STANDARDS_R.md` - Project coding conventions
- Output file: `data/wpa_challenge_values.json`
