import enum

""" Output Columns
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
"""

class MARKOV_WEIGHTS_DATA_DICTIONARY(enum.Enum):
    TIME_ELAPSED = "time_elapsed"
    SCORE_MARGIN = "score_margin"
    HOME_TEAM_SPREAD = "home_team_spread"
    SAMPLE_SIZE = "sample_size"
    AWAY5 = "p-5"
    AWAY4 = "p-4"
    AWAY3 = "p-3"
    AWAY2 = "p-2"
    AWAY1 = "p-1"
    EVEN = "p+0"
    HOME1 = "p+1"
    HOME2 = "p+2"
    HOME3 = "p+3"
    HOME4 = "p+4"
    HOME5 = "p+5"