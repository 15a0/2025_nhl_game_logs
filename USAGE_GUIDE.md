# NHL DFS Analytics v2.0 - Usage Guide

**Complete pipeline for calculating slate-specific GOI (Game Optimized Index) for DFS optimization.**

---

## Quick Start

### 1. Initialize Database

```python
from src.db import DBManager

db = DBManager("Data/nhl_stats.db")
db.init_db()
```

### 2. Fetch & Calculate Stats

```python
from src.api import NHLAPIClient
from src.stats import calculate_game_stats

client = NHLAPIClient()

# Fetch game data
boxscore = client.fetch_boxscore("2025020001")
pbp = client.fetch_play_by_play("2025020001")

# Calculate 13 stats
stats = calculate_game_stats(boxscore, pbp)

# Store in database
db.insert_game({
    "game_id": "2025020001",
    "date": boxscore.get("gameDate"),
    "season": boxscore.get("season"),
    "game_type": boxscore.get("gameType"),
    "home_team": boxscore.get("homeTeam", {}).get("abbrev"),
    "away_team": boxscore.get("awayTeam", {}).get("abbrev"),
    # ... other fields
})
db.insert_team_game_stats("2025020001", stats)
```

### 3. Aggregate Stats

```python
from src.aggregator import StatsAggregator

agg = StatsAggregator(db)

# Get season stats
season_stats = agg.get_season_stats("FLA", "2025-10-01", "2025-10-31")

# Get all teams season stats
all_teams_stats = agg.get_all_teams_season_stats("2025-10-01", "2025-10-31")

# Get league context (for z-scores)
league_context = agg.get_league_context("2025-10-01", "2025-10-31")
```

### 4. Calculate Z-Scores & TPI

```python
from src.calc import TPICalculator
import yaml

# Load config
with open("src/config/config.yaml") as f:
    config = yaml.safe_load(f)

# Calculate TPI
calc = TPICalculator(config)
tpi_results = calc.calculate_tpi_for_all_teams(all_teams_stats, league_context)

# Rank teams
rankings = calc.rank_teams(tpi_results)
summary = calc.get_tpi_summary(tpi_results, top_n=5)
```

### 5. Calculate Slate GOI

```python
from src.goi import SlateGOICalculator

# Get games for slate date
games = [
    {"game_id": "2025020001", "home_team": "FLA", "away_team": "CHI"},
    {"game_id": "2025020002", "home_team": "COL", "away_team": "NYR"},
    # ... more games
]

# Calculate Slate GOI
goi_calc = SlateGOICalculator(config)
slate_goi_games = goi_calc.calculate_slate_goi(
    games=games,
    team_stats=all_teams_stats,
    tpi_results=tpi_results,
    slate_date="2025-10-28"
)

# Prioritize games
prioritized = goi_calc.prioritize_games(slate_goi_games)

# Get summary
slate_summary = goi_calc.get_slate_summary(prioritized, top_n=3)
```

---

## Architecture Overview

### 5-Phase Pipeline

```
Phase 1: API + Stats
    ↓ (Fetch NHL data, calculate 13 stats)
Phase 2: Data Validation
    ↓ (Test against real NHL games)
Phase 3: DB + Aggregation
    ↓ (Store stats, aggregate by team/date)
Phase 4: Z-Score + TPI
    ↓ (Normalize stats, rank teams 1-32)
Phase 5: Slate GOI
    ↓ (Prioritize games for DFS slates)
Output: Stack recommendations
```

---

## Module Breakdown

### Phase 1: Data Collection & Calculation

#### `src/api/api_client.py` - NHL API Client
**Purpose**: Fetch data from NHL API with retry logic

**Methods**:
- `fetch_boxscore(game_id)` - Get game stats
- `fetch_play_by_play(game_id)` - Get play-by-play events
- `fetch_schedule_date(date_str)` - Get games for a date
- `fetch_current_season()` - Get current season ID
- `fetch_season_schedule(season_id)` - Get all games for season

**Features**:
- Exponential backoff retry (3 attempts)
- 15-second timeout
- Structured error handling
- Type hints + logging

**Example**:
```python
from src.api import NHLAPIClient

client = NHLAPIClient()
boxscore = client.fetch_boxscore("2025020001")
pbp = client.fetch_play_by_play("2025020001")
```

#### `src/stats/stats_calculator.py` - Stats Calculator
**Purpose**: Calculate 13 high-signal stats from raw data

**13 Stats**:
1. PP% - Power Play %
2. PK% - Penalty Kill %
3. FOW% - Faceoff Win %
4. CF% - Corsi For %
5. SCF% - Scoring Chances For %
6. HDC% - High-Danger Chances For %
7. HDCO% - High-Danger Chances On %
8. HDF% - High-Danger Shots For %
9. xGF - Expected Goals For
10. xGA - Expected Goals Against
11. Pen Taken/60 - Penalties per 60 min
12. Pen Drawn/60 - Penalties drawn per 60 min
13. Net Pen/60 - Net penalty advantage per 60 min

**Methods**:
- `calculate_game_stats(boxscore, pbp)` - Calculate all 13 stats

**Example**:
```python
from src.stats import calculate_game_stats

stats = calculate_game_stats(boxscore, pbp)
# Output: {
#     "FLA": {"cf_pct": 58.0, "xgf": 4.37, ...},
#     "CHI": {"cf_pct": 42.0, "xgf": 1.46, ...}
# }
```

#### `src/utils/` - Utility Functions
**Purpose**: Helper functions for xG and coordinates

**Files**:
- `xg_calculator.py` - Calculate expected goals (distance-based)
- `coordinate_utils.py` - Check high-danger zone, get zone name

**Example**:
```python
from src.utils import calculate_xg, is_high_danger

xg = calculate_xg(x=85, y=5, shot_type="Wrist")  # 0.22
in_hd = is_high_danger(x=85, y=5)  # True
```

---

### Phase 3: Data Persistence & Aggregation

#### `src/db/db_manager.py` - Database Manager
**Purpose**: SQLite database operations

**Schema**:
- `games` - Master game records (1 row per game)
- `team_game_stats` - Per-game stats (2 rows per game: home/away)
- `team_aggregates` - Aggregated stats (season + rolling windows)

**Methods**:
- `init_db()` - Create schema
- `insert_game(game_data)` - Store game
- `insert_team_game_stats(game_id, stats)` - Store team stats
- `query_team_stats(team, start_date, end_date)` - Query by team
- `query_game_stats(game_id)` - Query by game
- `game_exists(game_id)` - Check if processed
- `get_latest_game_date()` - Most recent game
- `get_team_list()` - All teams in DB

**Example**:
```python
from src.db import DBManager

db = DBManager("Data/nhl_stats.db")
db.init_db()
db.insert_game({"game_id": "2025020001", ...})
db.insert_team_game_stats("2025020001", stats)
```

#### `src/aggregator/aggregator.py` - Stats Aggregator
**Purpose**: Aggregate stats into rolling windows and season totals

**Methods**:
- `get_season_stats(team, start_date, end_date)` - Season totals
- `get_rolling_stats(team, end_date, games=5)` - Last N games
- `get_all_teams_season_stats(start_date, end_date)` - All teams season
- `get_all_teams_rolling_stats(end_date, games=5)` - All teams rolling
- `get_league_context(start_date, end_date)` - League mean/std (for z-scores)

**Example**:
```python
from src.aggregator import StatsAggregator

agg = StatsAggregator(db)
season = agg.get_season_stats("FLA", "2025-10-01", "2025-10-31")
last_5 = agg.get_rolling_stats("FLA", "2025-10-31", games=5)
league = agg.get_league_context("2025-10-01", "2025-10-31")
```

---

### Phase 4: Normalization & Team Rankings

#### `src/calc/zscore_calculator.py` - Z-Score Calculator
**Purpose**: Normalize stats using league context

**Z-Score Formula**:
```
z = (value - mean) / std_dev
```

**Methods**:
- `calculate_zscores(team_stats, league_context)` - Z-score each stat
- `calculate_average_zscore(z_scores, stats_to_include)` - Average across stats
- `calculate_bucket_zscores(z_scores, stat_buckets)` - Average per bucket
- `calculate_composite_zscore(bucket_zscores, stat_buckets)` - Weighted composite

**Example**:
```python
from src.calc import ZScoreCalculator

calc = ZScoreCalculator()
z_scores = calc.calculate_zscores(team_stats, league_context)
# Output: {"cf_pct": 0.67, "xgf": 0.4, ...}
```

#### `src/calc/tpi_calculator.py` - TPI Calculator
**Purpose**: Calculate Team Power Index (TPI) rankings

**TPI Formula**:
```
TPI = Weighted average of 3 buckets:
  - Offensive Creation (40%): CF%, xGF, PP%, etc.
  - Defensive Resistance (30%): xGA, PK%, Pen Taken/60
  - Pace Drivers (30%): FOW%, Pen Drawn/60, Net Pen/60
```

**Methods**:
- `calculate_tpi(team_stats, league_context)` - TPI for single team
- `calculate_tpi_for_all_teams(all_teams_stats, league_context)` - TPI for all teams
- `rank_teams(tpi_results)` - Rank teams 1-32
- `get_tpi_summary(tpi_results, top_n=10)` - Summary stats

**Example**:
```python
from src.calc import TPICalculator

calc = TPICalculator(config)
tpi_results = calc.calculate_tpi_for_all_teams(all_teams_stats, league_context)
rankings = calc.rank_teams(tpi_results)
# Output: [("FLA", 0.85, 1), ("COL", 0.72, 2), ...]
```

---

### Phase 5: Game Prioritization

#### `src/goi/slate_goi_calculator.py` - Slate GOI Calculator
**Purpose**: Prioritize games for DFS slates

**Slate GOI Formula**:
```
Slate GOI = 0.4 × Form (Last 5 games)
          + 0.3 × Matchup (Opponent quality)
          + 0.2 × Venue (Home +8%)
          + 0.1 × Rest (B2B penalty)
```

**Methods**:
- `calculate_slate_goi(games, team_stats, tpi_results, slate_date)` - Calculate GOI
- `prioritize_games(slate_goi_games)` - Rank by priority
- `_calculate_form_factor(home_stats, away_stats)` - Recent form
- `_calculate_matchup_factor(home_stats, away_stats)` - Opponent quality
- `_get_stack_recommendation(...)` - Stack suggestions
- `get_slate_summary(prioritized_games, top_n=3)` - Summary

**Stack Recommendations**:
1. **GOI Differential** - Stack stronger team (if diff > 1.5)
2. **PP/PK Mismatch** - Stack power play advantage (if mismatch > 15)
3. **High-Event Games** - Alert for high-scoring (both teams > 55% HDC%)

**Example**:
```python
from src.goi import SlateGOICalculator

calc = SlateGOICalculator(config)
slate_goi = calc.calculate_slate_goi(games, team_stats, tpi_results, "2025-10-28")
prioritized = calc.prioritize_games(slate_goi)
summary = calc.get_slate_summary(prioritized, top_n=3)
```

---

## How to Run the Pipeline

### Option 1: Manual Step-by-Step

```python
from src.api import NHLAPIClient
from src.stats import calculate_game_stats
from src.db import DBManager
from src.aggregator import StatsAggregator
from src.calc import TPICalculator
from src.goi import SlateGOICalculator
import yaml

# Load config
with open("src/config/config.yaml") as f:
    config = yaml.safe_load(f)

# Initialize
client = NHLAPIClient()
db = DBManager("Data/nhl_stats.db")
db.init_db()

# Fetch and store games
games = client.fetch_season_schedule()
for game in games[:5]:  # Example: first 5 games
    game_id = game["game_id"]
    boxscore = client.fetch_boxscore(game_id)
    pbp = client.fetch_play_by_play(game_id)
    stats = calculate_game_stats(boxscore, pbp)
    
    db.insert_game({
        "game_id": game_id,
        "date": game["date"],
        "season": boxscore.get("season"),
        "game_type": boxscore.get("gameType"),
        "home_team": game["home_team"],
        "away_team": game["away_team"],
        "home_team_id": boxscore.get("homeTeam", {}).get("id"),
        "away_team_id": boxscore.get("awayTeam", {}).get("id"),
        "game_state": boxscore.get("gameState"),
        "home_score": boxscore.get("homeTeam", {}).get("score"),
        "away_score": boxscore.get("awayTeam", {}).get("score")
    })
    db.insert_team_game_stats(game_id, stats)

# Aggregate
agg = StatsAggregator(db)
all_teams_stats = agg.get_all_teams_season_stats("2025-10-01", "2025-10-31")
league_context = agg.get_league_context("2025-10-01", "2025-10-31")

# Calculate TPI
tpi_calc = TPICalculator(config)
tpi_results = tpi_calc.calculate_tpi_for_all_teams(all_teams_stats, league_context)

# Calculate Slate GOI
slate_date = "2025-10-28"
slate_games = [g for g in games if g["date"] == slate_date]
goi_calc = SlateGOICalculator(config)
slate_goi = goi_calc.calculate_slate_goi(slate_games, all_teams_stats, tpi_results, slate_date)
prioritized = goi_calc.prioritize_games(slate_goi)

# Output
for game in prioritized[:3]:
    print(f"{game['priority_rank']}. {game['away_team']} @ {game['home_team']}")
    print(f"   Slate GOI: {game['slate_goi']}")
    print(f"   Recommendation: {game['stack_recommendation']}")
```

### Option 2: Run Validation Tests

```bash
# Phase 1 + 2 validation
python tests/test_phase2_validation.py

# Phase 3 validation
python tests/test_phase3_validation.py

# Phase 4 validation
python tests/test_phase4_validation.py

# Phase 5 validation
python tests/test_phase5_validation.py
```

---

## Configuration

### `src/config/config.yaml`

**API Configuration**:
```yaml
api:
  base_url: "https://api-web.nhle.com"
  timeout_seconds: 15
  max_retries: 3
  backoff_factor: 0.5
```

**High-Danger Zone**:
```yaml
high_danger_zone:
  x_threshold: 15        # feet from net
  y_threshold: 8.5       # feet from center
  net_x: 89              # net position
```

**xG Model**:
```yaml
xg_model:
  version: "1.0"
  high_danger_xg: {wrist: 0.22, slap: 0.17}
  mid_range_xg: {wrist: 0.10, slap: 0.08}
  long_range_xg: {wrist: 0.04, slap: 0.03}
```

**Slate GOI**:
```yaml
slate_goi:
  form_window: 5              # games
  venue_boost: 0.08           # +8% xGF for home
  rest_penalty: -0.05         # -5% for B2B
  early_season_weight: 10     # games
```

---

## Output Examples

### TPI Rankings
```
1. FLA: 0.85 (Offensive Creation: 0.5, Defensive Resistance: 0.0, Pace Drivers: 0.1)
2. COL: 0.72
3. NYR: 0.61
...
32. CHI: -0.82
```

### Slate GOI Prioritization
```
Priority 1: CHI @ FLA
  Slate GOI: 0.35
  Form Factor: 0.8
  Matchup Factor: -1.0
  Venue Factor: 0.08
  GOI Diff: 1.67
  Stack Recommendation: Stack FLA (GOI +1.7) | CHI PP stack

Priority 2: TOR @ BOS
  Slate GOI: 0.25
  ...

Priority 3: NYR @ COL
  Slate GOI: 0.15
  ...
```

---

## Next Steps

### Immediate (Next Session)
1. Build **Orchestrator** - End-to-end pipeline runner
2. Add **Logging** - Structured logs for debugging
3. Add **Error Handling** - Graceful failure modes

### Short-term (Week 1)
1. Deploy to **Production** - Nightly runs
2. Add **Caching** - Avoid redundant API calls
3. Add **Monitoring** - Track pipeline health

### Medium-term (Month 1)
1. Add **v2.1 xG Model** - Advanced shot modeling
2. Add **Strength State Filtering** - 5v5 vs PP analysis
3. Add **Game State Filtering** - Situationcode analysis
4. Add **TOI Normalization** - Per-60 stats accuracy

### Long-term (Q1 2026)
1. Add **Machine Learning** - Predictive models
2. Add **Backtesting** - Historical validation
3. Add **Web UI** - Interactive dashboard
4. Add **API** - External access

---

## Support

**Questions?**
- Check `PHASE*_VALIDATION.md` files for test examples
- Review `architecture_design_decisions.md` for design rationale
- Run validation tests to verify setup

**Issues?**
- Check logs in `logs/app.log`
- Verify config in `src/config/config.yaml`
- Ensure NHL API is accessible

---

**Version**: 2.0.0  
**Status**: Production-Ready  
**Last Updated**: October 28, 2025
