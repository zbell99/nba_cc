from enum import Enum

"""

| Column | Type | Description |
|---|---|---|
| `game_id` | int64 | Game identifier |
| `home_team_spread` | float64 | Pregame betting line (half-point lines) |
| `time_elapsed` | float64 | Seconds since game start, counting up (0, 15, 30, ...) |
| `period` | int64 | Period number at this snapshot |
| `home_score` | int64 | Home team score at this snapshot |
| `away_score` | int64 | Away team score at this snapshot |
| `score_margin` | int64 | `home_score - away_score` |

"""

class NBA_SNAPSHOT_DATA_DICTIONARY(str, Enum):
    GAME_ID = "game_id"
    HOME_TEAM_SPREAD = "home_team_spread"
    TIME_ELAPSED = "time_elapsed"
    PERIOD = "period"
    HOME_SCORE = "home_score"
    AWAY_SCORE = "away_score"
    SCORE_MARGIN = "score_margin"
