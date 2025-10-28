# Phase 3: DB Schema Design & Aggregation

**Status**: Complete  
**Date**: October 28, 2025  
**Objective**: Design SQLite schema and build aggregation layer

## What Phase 3 Delivers

Phase 3 creates the data persistence and aggregation layer:

1. ✅ **SQLite Schema** - Optimized for DFS analytics
2. ✅ **DBManager** - Class-based database operations
3. ✅ **StatsAggregator** - Rolling windows + season totals
4. ✅ **League Context** - Z-score normalization data

## Files Created

### 1. `src/db/__init__.py`
- DB module initialization

### 2. `src/db/db_manager.py` (Production-Grade)
- **DBManager class** with methods:
  - `init_db()` - Create schema
  - `insert_game()` - Store game record
  - `insert_team_game_stats()` - Store per-game stats (2 rows per game)
  - `query_team_stats()` - Query by team + date range
  - `query_game_stats()` - Query by game ID
  - `game_exists()` - Check if game processed
  - `get_latest_game_date()` - Get most recent game
  - `get_team_list()` - Get all teams in DB

- **Features**:
  - Context manager for connections
  - Automatic schema creation
  - Indexes for common queries
  - Two-row-per-game pattern
  - Type hints + docstrings

### 3. `src/aggregator/__init__.py`
- Aggregator module initialization

### 4. `src/aggregator/aggregator.py` (Production-Grade)
- **StatsAggregator class** with methods:
  - `get_season_stats()` - Aggregate season totals
  - `get_rolling_stats()` - Aggregate last N games
  - `get_all_teams_season_stats()` - All teams, season
  - `get_all_teams_rolling_stats()` - All teams, rolling
  - `get_league_context()` - League-wide mean/std for z-scores

- **Features**:
  - Rolling window support (5, 10, custom)
  - Date range queries
  - League-wide aggregation
  - Z-score normalization context
  - Type hints + docstrings

## SQLite Schema

### Table 1: `games`
Master game records (one row per game)

```sql
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    season INTEGER NOT NULL,
    game_type INTEGER NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_team_id INTEGER,
    away_team_id INTEGER,
    game_state TEXT,
    home_score INTEGER,
    away_score INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

**Indexes**:
- `idx_games_date` - Query by date
- `idx_games_teams` - Query by teams

### Table 2: `team_game_stats`
Per-game stats (two rows per game: one per team)

```sql
CREATE TABLE team_game_stats (
    id INTEGER PRIMARY KEY,
    game_id TEXT NOT NULL,
    date TEXT NOT NULL,
    team TEXT NOT NULL,
    team_id INTEGER,
    side TEXT,  -- 'home' or 'away'
    
    -- Tier 1 (Boxscore)
    pp_pct REAL,
    pk_pct REAL,
    fow_pct REAL,
    
    -- Tier 2-4 (Play-by-Play)
    cf_pct REAL,
    scf_pct REAL,
    hdc_pct REAL,
    hdco_pct REAL,
    hdf_pct REAL,
    xgf REAL,
    xga REAL,
    pen_taken_60 INTEGER,
    pen_drawn_60 INTEGER,
    net_pen_60 INTEGER,
    
    created_at TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    UNIQUE(game_id, team)
)
```

**Indexes**:
- `idx_team_game_stats_game` - Query by game ID
- `idx_team_game_stats_team_date` - Query by team + date

### Table 3: `team_aggregates`
Aggregated stats (season + rolling windows)

```sql
CREATE TABLE team_aggregates (
    id INTEGER PRIMARY KEY,
    team TEXT NOT NULL,
    team_id INTEGER,
    date TEXT NOT NULL,
    window TEXT NOT NULL,  -- 'season', 'last_5', 'last_10', etc.
    games_count INTEGER,
    
    -- Aggregated stats (averages)
    pp_pct_avg REAL,
    pk_pct_avg REAL,
    fow_pct_avg REAL,
    cf_pct_avg REAL,
    scf_pct_avg REAL,
    hdc_pct_avg REAL,
    hdco_pct_avg REAL,
    hdf_pct_avg REAL,
    xgf_avg REAL,
    xga_avg REAL,
    pen_taken_60_avg REAL,
    pen_drawn_60_avg REAL,
    net_pen_60_avg REAL,
    
    created_at TIMESTAMP,
    UNIQUE(team, date, window)
)
```

**Indexes**:
- `idx_team_aggregates_team_date` - Query by team + date

## Two-Row-Per-Game Pattern

Each game has exactly 2 rows in `team_game_stats`:

```
game_id: 2025020001
  Row 1: team=FLA, side=home, cf_pct=58.0, xgf=4.37, ...
  Row 2: team=CHI, side=away, cf_pct=42.0, xgf=1.46, ...
```

**Benefits**:
- ✅ Efficient queries by team
- ✅ Easy to calculate team stats
- ✅ Supports rolling windows
- ✅ Minimal data duplication

## Usage Examples

### Initialize Database

```python
from src.db import DBManager

db = DBManager("Data/nhl_stats.db")
db.init_db()
```

### Insert Game Stats

```python
# From Phase 1 stats_calculator output
game_stats = {
    "FLA": {"cf_pct": 58.0, "xgf": 4.37, ...},
    "CHI": {"cf_pct": 42.0, "xgf": 1.46, ...}
}

db.insert_game({"game_id": "2025020001", "date": "2025-10-07", ...})
db.insert_team_game_stats("2025020001", game_stats)
```

### Query Team Stats

```python
from src.aggregator import StatsAggregator

agg = StatsAggregator(db)

# Season stats
season_stats = agg.get_season_stats("FLA", "2025-10-01", "2025-10-31")
# Output: {'games_count': 10, 'cf_pct_avg': 52.3, 'xgf_avg': 3.2, ...}

# Last 5 games
last_5 = agg.get_rolling_stats("FLA", "2025-10-31", games=5)
# Output: {'games_count': 5, 'cf_pct_avg': 54.1, 'xgf_avg': 3.5, ...}

# League context (for z-scores)
league = agg.get_league_context("2025-10-01", "2025-10-31")
# Output: {'cf_pct': {'mean': 50.0, 'std': 3.2}, 'xgf': {'mean': 2.8, 'std': 0.5}, ...}
```

## Next: Phase 4 (Z-Score + TPI)

Once Phase 3 is validated, we'll build:

1. **zscore_calculator.py** - Z-score normalization (from v1.0 logic)
2. **tpi_calculator.py** - TPI calculation (bucketed z-scores)

These will use:
- League context (mean/std) from aggregator
- Team stats (season + rolling) from aggregator
- Bucketing logic from config

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Two-row-per-game | Efficient team queries, minimal duplication |
| Separate aggregates table | Pre-computed averages for fast z-score calc |
| Context manager for DB | Automatic connection handling, error safety |
| Indexes on common queries | Fast lookups by team, date, game |
| UNIQUE constraints | Prevent duplicate stats insertion |
| Type hints throughout | IDE support, error detection |

## Performance Considerations

**Query Performance**:
- `team_game_stats` indexed on (team, date) → O(log n) lookups
- `games` indexed on date → O(log n) range queries
- Aggregates pre-computed → O(1) access

**Storage**:
- ~13 columns × 2 rows per game × 1,230 games/season = ~32K rows
- Estimated DB size: 5-10 MB per season

**Scalability**:
- Schema supports multiple seasons
- Indexes scale efficiently
- Aggregation layer is modular

## Status

✅ Phase 3 Complete
- Schema designed (3 tables, 3 indexes)
- DBManager implemented (8 methods)
- StatsAggregator implemented (5 methods)
- Production-ready code (type hints, logging, docstrings)

⏭️ Phase 4: Z-Score + TPI (next)
⏭️ Phase 5: Slate GOI (following)

## Ready for Phase 4?

Phase 3 provides the data foundation for z-score calculations and TPI. Ready to proceed!
