# Architecture & Design Decisions

**Document Purpose**: Detailed design decisions for modular architecture, class design, error handling, config management, testing, and public artifacts.

**Status**: Design Phase (ready for implementation)  
**Last Updated**: October 28, 2025

---

## Table of Contents

1. [The 13 High-Signal Stats Reference](#the-13-high-signal-stats-reference)
2. [Strategic Evolution: From Season GOI to Slate GOI](#strategic-evolution-from-season-goi-to-slate-goi)
3. [Design Rationale & Assumptions](#design-rationale--assumptions)
4. [Collaborative Development Model: You, Me, and GROK](#collaborative-development-model-you-me-and-grok)
5. [GROK's 7 Enhancements (v2.0 Refinements)](#groks-7-enhancements-v20-refinements)
6. [TPI Evolution: From Manual Input to Automatic Byproduct](#tpi-evolution-from-manual-input-to-automatic-byproduct)
7. [Module Names](#module-names)
8. [DB Manager: Class vs Functions](#db-manager-class-vs-functions)
9. [Error Handling Strategy](#error-handling-strategy)
10. [Config Management](#config-management)
11. [Testing Strategy](#testing-strategy)
12. [Public Directory](#public-directory)
13. [Final Project Structure](#final-project-structure)

---

## The 13 High-Signal Stats Reference

**Context**: The term "13 high-signal stats" refers to the core advanced analytics metrics calculated from each NHL game. These stats are derived from NHL API boxscore and play-by-play data and form the foundation for TPI and GOI calculations. This reference ensures clarity and consistency across all documentation and code.

### The 13 Stats: Overview & DFS Relevance

| # | Stat | Type | Source | Purpose | DFS Relevance (2–3 Game Slates) |
|---|------|------|--------|---------|------|
| 1 | **Net Pen/60** | Derived | Play-by-Play + TOI | Discipline: net penalty advantage per 60 min | More 5v5 time, fewer SHG against |
| 2 | **Pen Drawn/60** | Derived | Play-by-Play + TOI | Discipline: penalties drawn per 60 min | PP opportunities = boom/bust |
| 3 | **Pen Taken/60** | Derived | Play-by-Play + TOI | Discipline: penalties taken per 60 min | PK time = reduced scoring |
| 4 | **CF%** | Derived | Play-by-Play | Pace: Corsi For % (shot attempts) | Puck possession = more shots = more DK points |
| 5 | **SCF%** | Derived | Play-by-Play | Offense: Scoring Chances For % | Quality chances = higher goal probability |
| 6 | **HDF%** | Derived | Play-by-Play | Offense: High-Danger Shots For % | Slot control = high-value scoring |
| 7 | **HDC%** | Derived | Play-by-Play | Offense: High-Danger Chances For % | Slot control = high-value scoring |
| 8 | **HDCO%** | Derived | Play-by-Play | Offense: High-Danger Chances On (net) % | Slot control = high-value scoring |
| 9 | **xGF** | Derived | Play-by-Play + xG Model | Offense: Expected Goals For | True talent beyond results |
| 10 | **xGA** | Derived | Play-by-Play + xG Model | Defense: Expected Goals Against | True talent beyond results |
| 11 | **PP%** | Direct | Boxscore | Offense: Power Play % | Special teams = boom/bust in small samples |
| 12 | **PK%** | Direct | Boxscore | Defense: Penalty Kill % | Special teams = boom/bust in small samples |
| 13 | **FOW%** | Direct | Boxscore | Pace: Faceoff Win % | Zone starts, PP possession |

### Stat Definitions & Calculations

#### **Offensive Creation Bucket** (Bucket Weight: 0.4)
- **CF%**: `Corsi For / (Corsi For + Corsi Against) × 100`
  - Corsi = all shot attempts (goals, shots on goal, missed shots, blocked shots)
  - Source: Play-by-play events with `eventTypeId` in ["SHOT", "MISSED_SHOT", "BLOCKED_SHOT"]
  
- **SCF%**: `Scoring Chances For / (SCF + SCA) × 100`
  - Scoring Chances = high-quality shot opportunities (rebounds, rush chances, etc.)
  - Source: Play-by-play with shot type and location classification
  
- **HDF%**: `High-Danger Shots For / (HDSF + HDSA) × 100`
  - High-Danger Shots = shots from inner slot (within 15 ft of net, between goal posts)
  - Source: Play-by-play with `xCoord`, `yCoord` filtering
  
- **HDC%**: `High-Danger Chances For / (HDCF + HDCA) × 100`
  - High-Danger Chances = all high-danger events (shots + blocked shots)
  - Source: Play-by-play with location filtering
  
- **HDCO%**: `High-Danger Chances On / (HDCO + High-Danger Chances Against) × 100`
  - High-Danger Chances On = high-danger shots that reached goalie (on net)
  - Source: Play-by-play with `eventTypeId` = "SHOT" and high-danger location
  
- **xGF**: `Sum of expected goals for all shots`
  - Expected Goals = probability of goal based on shot distance, angle, type, strength
  - Source: Play-by-play with xG model applied to each shot
  - Inputs: `xCoord`, `yCoord`, `shotType`, `strength`
  
- **PP%**: `Power Play Goals / Power Play Opportunities × 100`
  - Direct metric from boxscore
  - Source: Boxscore `powerPlayGoals` / `powerPlayOpportunities`

#### **Defensive Resistance Bucket** (Bucket Weight: 0.3, reversed)
- **xGA**: `Sum of expected goals against for all opponent shots`
  - Expected Goals Against = probability of goal against based on opponent shots
  - Source: Play-by-play with xG model applied to opponent shots
  - Inputs: `xCoord`, `yCoord`, `shotType`, `strength`
  - **Note**: Reversed in z-score calculation (lower is better)
  
- **PK%**: `(PP Opportunities Against - PP Goals Against) / PP Opportunities Against × 100`
  - Direct metric from boxscore
  - Source: Boxscore `powerPlayOpportunitiesAgainst`, `powerPlayGoalsAgainst`
  - **Note**: Reversed in z-score calculation (higher is better, but lower xGA is better)
  
- **Pen Taken/60**: `Penalties Taken / (TOI in minutes) × 60`
  - Penalties Taken = count of penalty events where team is offender
  - Source: Play-by-play `eventTypeId` = "PENALTY" filtered by offending player's team
  - TOI: Boxscore `playerByGameStats[i].toi` (summed for team)
  - **Note**: Reversed in z-score calculation (lower is better)

#### **Pace Drivers Bucket** (Bucket Weight: 0.3)
- **FOW%**: `Faceoffs Won / (Faceoffs Won + Faceoffs Lost) × 100`
  - Direct metric from boxscore
  - Source: Boxscore `teamStats.faceoffWinningPct` or per-player faceoff data
  
- **Pen Drawn/60**: `Penalties Drawn / (TOI in minutes) × 60`
  - Penalties Drawn = count of penalty events where team draws penalty
  - Source: Play-by-play `eventTypeId` = "PENALTY" filtered by `drewPenalty` field
  - TOI: Boxscore `playerByGameStats[i].toi` (summed for team)
  
- **Net Pen/60**: `(Penalties Taken - Penalties Drawn) / (TOI in minutes) × 60`
  - Net advantage in penalty differential per 60 minutes
  - Source: Combination of penalties taken and drawn
  - **Note**: Positive = more penalties drawn than taken (advantage)

### High-Danger Classification

```python
def is_high_danger(x, y, team_side):
    """
    Classify a shot as high-danger based on rink coordinates.
    
    Args:
        x: x-coordinate from play-by-play (rink coordinates: -100 to 100)
        y: y-coordinate from play-by-play (rink coordinates: -42.5 to 42.5)
        team_side: "right" (attacking 89) or "left" (attacking -89)
    
    Returns:
        bool: True if shot is in high-danger area (inner slot)
    """
    net_x = 89 if team_side == "right" else -89
    # Inner slot: within 15 ft of net, between goal posts (±8.5 ft)
    return abs(x - net_x) < 15 and abs(y) < 8.5
```

### xG Model Inputs

The NHL API provides all inputs needed for xG calculation. You can:
1. Use public xG models (e.g., Evolving-Hockey, MoneyPuck)
2. Build a simple logistic model on historical data
3. Use NHL Edge data (if available via API later)

**Inputs available from play-by-play**:
- `xCoord`, `yCoord` → Shot distance and angle
- `shotType` → Wrist, slap, tip-in, etc.
- `strength` → 5v5, 5v4, 4v5, etc.
- Previous event → Rebound or rush detection

### Data Availability in NHL API

| Data Needed | Available? | Endpoint | JSON Path |
|-------------|-----------|----------|-----------|
| Penalties (Taken/Drawn) | ✅ Yes | Play-by-Play | `plays → eventTypeId: "PENALTY"` |
| TOI (Time on Ice) | ✅ Yes | Boxscore | `playerByGameStats.homeTeam.skaters[i].toi` |
| Shots (Corsi) | ✅ Yes | Play-by-Play | `eventTypeId: "SHOT", "BLOCKED_SHOT", "MISSED_SHOT"` |
| High-Danger Shots | ✅ Yes | Play-by-Play | `shotType, xCoord, yCoord` (classify via location) |
| Scoring Chances | ✅ Yes | Play-by-Play | Shot type + location classification |
| Faceoffs | ✅ Yes | Boxscore | `teamStats.faceoffWinningPct` |
| Power Plays | ✅ Yes | Boxscore | `powerPlayGoals, powerPlayOpportunities` |
| Shot Location (x,y) | ✅ Yes | Play-by-Play | `xCoord, yCoord` (rink coordinates) |
| Shot Type | ✅ Yes | Play-by-Play | `shotType` |
| Game State | ✅ Yes | Play-by-Play | `strength` (5v5, 5v4, 4v5, etc.) |

### Team-Level vs Player-Level

Most stats are calculated at **team-level** for this project. However, the underlying data supports player-level analysis:

| Stat | Team-Level | Player-Level |
|------|-----------|--------------|
| PP%, PK%, FOW% | ✅ Yes | ❌ No (team only) |
| CF%, SCF%, xGF% | ✅ Yes | ✅ Yes (filter by playerId) |
| Pen/60, Pen Drawn/60 | ❌ No | ✅ Yes (requires TOI) |
| HDC%, HDCO% | ✅ Yes | ✅ Yes (filter by playerId) |

**Example**: Player-level Net Pen/60 calculation:
```python
# From play-by-play
penalties_taken = count(events where playerId == X and event == "PENALTY")
penalties_drawn = count(events where drewPenalty == X)

# From boxscore
toi_seconds = player["toi"]  # "18:45" → 1125 seconds
toi_minutes = toi_seconds / 60

net_pen_60 = (penalties_taken - penalties_drawn) / toi_minutes * 60
```

### Summary: All 13 Stats Are Available

✅ **YES — 100% YES.** The NHL boxscore and play-by-play endpoints provide ALL raw ingredients to calculate every single one of the 13 high-signal stats. Some are direct (PP%, PK%, FOW%), others are derived from event-level data (CF%, SCF%, xGF, xGA), and a few require TOI normalization (Pen/60, Pen Drawn/60).

---

## Module Names

**Decision**: ✅ **Approved as proposed**

| Module | Purpose | Rationale |
|--------|---------|-----------|
| `api_client.py` | NHL API fetching | Clear intent: client for external API |
| `data_parser.py` | Parse JSON responses | Separates fetching from parsing |
| `stats_calculator.py` | All stat calculations | Core "gold" logic; single responsibility |
| `db_manager.py` | SQLite operations | All DB interactions in one place |
| `utils.py` | Helpers, constants | xG model, shared functions |

**Why This Works**:
- ✅ Self-documenting (name tells you what it does)
- ✅ Easy to find code (grep for "xG" → `utils.py`)
- ✅ Scales as you add features (e.g., `goi_calculator.py` later)

---

## DB Manager: Class vs Functions

### Option A: Functions (Procedural)

```python
# db_manager.py
def init_db():
    conn = sqlite3.connect(DB_PATH)
    # ...

def insert_game(game_id, date, away_team, home_team):
    conn = sqlite3.connect(DB_PATH)
    # ...

def query_team_stats(team, start_date, end_date):
    conn = sqlite3.connect(DB_PATH)
    # ...
```

**Pros**:
- ✅ Simple, straightforward
- ✅ No state management
- ✅ Easy to test (pure functions)

**Cons**:
- ❌ Repeated connection logic
- ❌ No connection pooling
- ❌ Hard to manage transactions
- ❌ Difficult to add logging/monitoring per operation

---

### Option B: Class (OOP)

```python
# db_manager.py
class DBManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
    
    def init_db(self):
        # Uses self.conn
        pass
    
    def insert_game(self, game_id, date, away_team, home_team):
        # Uses self.conn
        pass
    
    def query_team_stats(self, team, start_date, end_date):
        # Uses self.conn
        pass
    
    def close(self):
        if self.conn:
            self.conn.close()
```

**Pros**:
- ✅ Single connection per instance (efficient)
- ✅ Easy to add logging, error handling
- ✅ Can manage transactions cleanly
- ✅ Context manager support (`with DBManager() as db:`)
- ✅ Scales well (add caching, retry logic later)

**Cons**:
- ❌ Slightly more complex
- ❌ Need to manage lifecycle (connect/close)

---

### **Recommendation: Class (Option B)**

**Why**:
1. **Connection efficiency**: Reuse one connection instead of creating new ones
2. **Logging**: Easy to add per-operation logging
3. **Transactions**: Can wrap multi-step operations in transactions
4. **Future-proof**: Easy to add caching, connection pooling, retry logic
5. **Context manager**: Can use `with` statement for clean resource management

**Implementation**:
```python
class DBManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    # ... methods ...
```

**Usage**:
```python
with DBManager(DB_PATH) as db:
    db.insert_game(2025020001, "2025-10-07", "CHI", "FLA")
    db.insert_game_stats(2025020001, "FLA", stats_dict)
```

---

## Error Handling Strategy

### Option A: Centralized (`error_handler.py`)

```python
# error_handler.py
class APIError(Exception):
    pass

class ParseError(Exception):
    pass

class DBError(Exception):
    pass

def handle_api_error(func):
    """Decorator for API calls"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.RequestException as e:
            raise APIError(f"API call failed: {e}")
    return wrapper
```

**Pros**:
- ✅ Centralized exception definitions
- ✅ Consistent error messages
- ✅ Easy to add global error handling

**Cons**:
- ❌ Separate file adds complexity
- ❌ Overkill for small project
- ❌ Modules still need to import from it

---

### Option B: Distributed (Each Module Handles Its Own)

```python
# api_client.py
class APIError(Exception):
    pass

def fetch_boxscore(game_id):
    try:
        response = requests.get(BOXSCORE_URL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise APIError(f"Failed to fetch boxscore: {e}")

# data_parser.py
class ParseError(Exception):
    pass

def parse_boxscore(data):
    try:
        # Parse logic
    except (KeyError, TypeError) as e:
        raise ParseError(f"Invalid boxscore format: {e}")

# db_manager.py
class DBError(Exception):
    pass

def insert_game(self, ...):
    try:
        # DB logic
    except sqlite3.Error as e:
        raise DBError(f"Database error: {e}")
```

**Pros**:
- ✅ Each module is self-contained
- ✅ Easy to understand (error handling near the code)
- ✅ Simpler for small projects
- ✅ Less coupling between modules

**Cons**:
- ❌ Duplicate exception definitions
- ❌ Harder to catch all errors globally

---

### Option C: Hybrid (Best of Both)

```
error_handler.py (base exceptions)
├── APIError
├── ParseError
├── DBError
└── ValidationError

Each module imports from error_handler and raises specific exceptions
```

**Pros**:
- ✅ Centralized exception hierarchy
- ✅ Each module still handles its own logic
- ✅ Orchestrator can catch specific errors
- ✅ Scalable

**Cons**:
- ❌ Minimal (just one small file)

---

### **Recommendation: Hybrid (Option C)**

**Why**:
1. **Clarity**: Exception names tell you what went wrong
2. **Scalability**: Easy to add new exception types
3. **Orchestrator**: Can catch specific errors and retry/log appropriately
4. **Minimal overhead**: Just one small file with base exceptions

**Implementation**:
```python
# modules/error_handler.py
class NHLGameLogsError(Exception):
    """Base exception for all NHL Game Logs errors"""
    pass

class APIError(NHLGameLogsError):
    """Raised when NHL API call fails"""
    pass

class ParseError(NHLGameLogsError):
    """Raised when data parsing fails"""
    pass

class DBError(NHLGameLogsError):
    """Raised when database operation fails"""
    pass

class ValidationError(NHLGameLogsError):
    """Raised when input validation fails"""
    pass
```

**Usage in modules**:
```python
# api_client.py
from modules.error_handler import APIError

def fetch_boxscore(game_id):
    try:
        response = requests.get(BOXSCORE_URL)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise APIError(f"Failed to fetch boxscore for {game_id}: {e}")
```

**Usage in orchestrator**:
```python
from modules.error_handler import APIError, DBError

try:
    process_game(game_id)
except APIError as e:
    logger.error(f"API error: {e}")
    # Retry logic
except DBError as e:
    logger.error(f"DB error: {e}")
    # Rollback logic
```

---

## Config Management

### Option A: `utils.py` (Constants)

```python
# utils.py
BOXSCORE_URL_TEMPLATE = "https://api-web.nhle.com/v1/gamecenter/{}/boxscore"
PLAY_BY_PLAY_URL_TEMPLATE = "https://api-web.nhle.com/v1/gamecenter/{}/play-by-play"
DB_PATH = "Data/nhl_stats.db"
API_TIMEOUT = 10
```

**Pros**:
- ✅ Simple
- ✅ All constants in one place

**Cons**:
- ❌ Hardcoded values
- ❌ Can't easily change per environment (dev/prod)
- ❌ Not suitable for secrets or sensitive data

---

### Option B: YAML Config (`config/config.yaml`)

```yaml
# config/config.yaml
database:
  path: "Data/nhl_stats.db"
  timeout: 30

api:
  boxscore_url: "https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"
  play_by_play_url: "https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
  timeout: 10
  rate_limit_delay: 0.5

logging:
  level: "INFO"
  file: "logs/orchestrator.log"

stats:
  xg_model: "simple"
  high_danger_x_threshold: 15
  high_danger_y_threshold: 8.5
```

**Pros**:
- ✅ Human-readable
- ✅ Easy to change without code changes
- ✅ Environment-specific configs (dev.yaml, prod.yaml)
- ✅ Scalable for future features

**Cons**:
- ❌ Extra file to manage
- ❌ Need YAML parser

---

### **Recommendation: Hybrid (YAML + Defaults)**

**Why**:
1. **Flexibility**: Change config without touching code
2. **Environment-aware**: Different configs for dev/test/prod
3. **Maintainability**: Non-developers can adjust settings
4. **Scalability**: Easy to add new config sections

**Implementation**:
```python
# modules/config.py
import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    "database": {
        "path": "Data/nhl_stats.db",
        "timeout": 30
    },
    "api": {
        "timeout": 10,
        "rate_limit_delay": 0.5
    },
    "logging": {
        "level": "INFO",
        "file": "logs/orchestrator.log"
    }
}

def load_config(config_file="config/config.yaml"):
    """Load config from YAML, fall back to defaults"""
    if Path(config_file).exists():
        with open(config_file, 'r') as f:
            user_config = yaml.safe_load(f)
            return {**DEFAULT_CONFIG, **user_config}
    return DEFAULT_CONFIG

CONFIG = load_config()
```

**Usage**:
```python
from modules.config import CONFIG

db_path = CONFIG["database"]["path"]
api_timeout = CONFIG["api"]["timeout"]
```

**File Structure**:
```
config/
├── config.yaml          (User-editable)
├── config.example.yaml  (Template, in git)
└── config.dev.yaml      (Optional: dev overrides)
```

---

## Testing Strategy

### Structure

```
tests/
├── __init__.py
├── test_api_client.py
├── test_data_parser.py
├── test_stats_calculator.py
├── test_db_manager.py
├── test_utils.py
└── fixtures/
    ├── sample_boxscore.json
    ├── sample_pbp.json
    └── sample_game_stats.json
```

### Framework: `pytest`

**Why pytest**:
- ✅ Simple, readable syntax
- ✅ Fixtures for test data
- ✅ Parametrized tests
- ✅ Easy to run (`pytest` or `pytest tests/test_api_client.py`)
- ✅ Good coverage reporting

### Example Test

```python
# tests/test_stats_calculator.py
import pytest
from modules.stats_calculator import calculate_xg, compute_corsi

def test_calculate_xg_close_range():
    """xG should be high for close shots"""
    xg = calculate_xg(x=75, y=0, shot_type="Wrist")
    assert xg == 0.2

def test_calculate_xg_far_range():
    """xG should be low for far shots"""
    xg = calculate_xg(x=0, y=0, shot_type="Wrist")
    assert xg == 0.05

@pytest.fixture
def sample_plays():
    """Load sample play-by-play data"""
    with open("tests/fixtures/sample_pbp.json") as f:
        return json.load(f)

def test_compute_corsi(sample_plays):
    """Corsi calculation should match expected values"""
    cf, ca = compute_corsi(sample_plays, team_id=13)
    assert cf == 25
    assert ca == 20
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_stats_calculator.py

# Run with coverage
pytest --cov=modules tests/

# Run with verbose output
pytest -v
```

### Recommendation

**Start with**:
- ✅ Unit tests for `stats_calculator.py` (core logic)
- ✅ Unit tests for `utils.py` (xG model, helpers)
- ✅ Integration test for `api_client.py` + `data_parser.py`
- ✅ Mock DB tests for `db_manager.py` (don't touch real DB)

**Later**:
- End-to-end tests (full orchestrator run)
- Performance tests (large datasets)

---

## Public Directory

### Purpose

A **visible, non-gitignored** directory for:
- Sample data files (for debugging)
- Test fixtures
- Reference documents
- Example outputs
- Files you want to inspect without git restrictions

### Structure

```
public/
├── README.md                    (What's in here)
├── sample_data/
│   ├── boxscore_sample.json     (Real API response example)
│   ├── pbp_sample.json          (Real play-by-play example)
│   └── game_stats_sample.csv    (Expected output format)
├── test_fixtures/
│   ├── minimal_pbp.json         (Minimal test case)
│   └── edge_case_pbp.json       (Edge cases: empty plays, etc.)
├── reference/
│   ├── api_field_mapping.md     (Field name reference)
│   └── stat_formulas.md         (Stat calculation formulas)
└── examples/
    ├── orchestrator_usage.txt   (How to run orchestrator)
    └── query_examples.sql       (Common DB queries)
```

### Why This Works

**Pros**:
- ✅ Always visible (not in .gitignore)
- ✅ Easy to share with external reviewers
- ✅ Useful for debugging (copy sample data, test locally)
- ✅ Reference material stays accessible
- ✅ Separate from code (cleaner repo)

**Cons**:
- ❌ Adds one more directory (minimal)

### `.gitignore` Update

```
# .gitignore
*.db
*.sqlite
*.sqlite3
Data/nhl_stats.db

# But DO track public/
!public/
```

---

## Final Project Structure

```
NHLGameLogs/
├── config/
│   ├── config.yaml              (User config - stat definitions, bucket weights, GOI params)
│   ├── config.example.yaml      (Template for reference)
│   └── config.dev.yaml          (Dev overrides, optional)
│
├── scripts/
│   ├── orchestrator.py          (Main entry point - coordinates entire pipeline)
│   ├── get_game_detail.py       (Wrapper - fetches & calculates stats for single game)
│   └── modules/
│       ├── __init__.py
│       ├── api_client.py        (NHL API fetching - boxscore & play-by-play)
│       ├── data_parser.py       (Parse JSON responses - extract relevant fields)
│       ├── stats_calculator.py  (Calculate 13 advanced stats per game - Corsi, xG, HDC, etc.)
│       ├── db_manager.py        (SQLite operations - class-based, connection lifecycle)
│       ├── aggregator.py        (Roll up game-level stats to team/date ranges)
│       ├── zscore_calculator.py (Z-score normalization & directional adjustment - adapted from v1.0)
│       ├── tpi_calculator.py    (TPI calculation - bucketed z-scores with weights)
│       ├── goi_calculator.py    (GOI calculation - matchup-level opportunity index)
│       ├── guardrails.py        (Apply GOI guardrails - early-season caps, hot goalie alerts, etc.)
│       ├── error_handler.py     (Custom exceptions - APIError, ParseError, DBError, etc.)
│       ├── config.py            (Config loading - YAML with defaults)
│       └── utils.py             (Helpers - xG model, constants, shared functions)
│
├── tests/
│   ├── __init__.py
│   ├── test_api_client.py
│   ├── test_data_parser.py
│   ├── test_stats_calculator.py
│   ├── test_db_manager.py
│   ├── test_aggregator.py
│   ├── test_zscore_calculator.py
│   ├── test_tpi_calculator.py
│   ├── test_goi_calculator.py
│   ├── test_utils.py
│   └── fixtures/
│       ├── sample_boxscore.json
│       ├── sample_pbp.json
│       ├── sample_game_stats.json
│       ├── minimal_pbp.json     (Edge case: empty plays)
│       └── edge_case_pbp.json   (Edge case: future game)
│
├── public/
│   ├── README.md
│   ├── sample_data/
│   │   ├── boxscore_sample.json
│   │   ├── pbp_sample.json
│   │   └── game_stats_sample.csv
│   ├── test_fixtures/
│   │   ├── minimal_pbp.json
│   │   └── edge_case_pbp.json
│   ├── reference/
│   │   ├── api_field_mapping.md
│   │   ├── stat_formulas.md
│   │   └── goi_v1_reference.md  (v1.0 GOI model reference)
│   └── examples/
│       ├── orchestrator_usage.txt
│       ├── query_examples.sql
│       └── config_example.yaml
│
├── Data/
│   ├── nhl_stats.db             (SQLite, gitignored)
│   ├── game_ids_cache.json
│   └── schedule.csv
│
├── db_setup/
│   ├── schema.sql
│   └── init_db.py
│
├── docs/
│   ├── api_reference.md
│   ├── orchestrator_requirements.md
│   ├── architecture_design_decisions.md
│   ├── class_design_analysis.md
│   ├── InitGitRepo.txt
│   ├── scaffodling.md
│   └── debug_pbp.json
│
├── logs/
│   └── orchestrator.log         (Generated at runtime)
│
├── .gitignore
├── README.md
└── requirements.txt
```

---

## Summary of Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Module Names | ✅ Approved | Self-documenting, clear intent |
| DB Manager | Class (OOP) | Connection efficiency, logging, transactions |
| Error Handling | Hybrid (error_handler.py) | Centralized exceptions, distributed handling |
| Config | YAML + defaults | Flexible, environment-aware, maintainable |
| Testing | pytest + fixtures | Simple, scalable, good coverage |
| Public Dir | Yes | Visible reference, debugging, sharing |

---

## Next Steps

1. **Create directory structure** (scripts/modules/, tests/, public/, config/)
2. **Create `modules/error_handler.py`** (base exceptions)
3. **Create `modules/config.py`** (config loading)
4. **Refactor `get_game_detail.py`** into modules:
   - Extract API calls → `api_client.py`
   - Extract parsing → `data_parser.py`
   - Extract calculations → `stats_calculator.py`
   - Extract helpers → `utils.py`
5. **Create `modules/db_manager.py`** (class-based DB operations)
6. **Create `tests/`** with unit tests
7. **Create `public/`** with sample data and reference docs
8. **Create `orchestrator.py`** (main entry point)

---

## Strategic Evolution: From Season GOI to Slate GOI

**The Core Insight**: Slate context > season context.

A team with 55% CF% on the season is good. A team with 62% CF% over the last 5 games vs. weak defense is a **stack target**. This is the difference between 1st and 100th place in a 2–3 game DFS slate.

### What v1.0 Season GOI Misses

| Factor | Impact |
|--------|--------|
| **Form** | Hot/cold streaks over last 5–10 games |
| **Matchup** | Opponent quality (xGA allowed, PK%) |
| **Venue** | Home/road splits (home +8% xGF) |
| **Rest** | Back-to-back penalty, travel fatigue |

### Expected Edge Improvement (v2.0 Slate GOI)

| Factor | Edge Gain |
|--------|-----------|
| Last 5 games vs. season | +15–25% |
| Matchup adjustment (xGA allowed) | +10–20% |
| Venue (home +8% xGF) | +5–10% |
| Rest (B2B penalty) | +3–7% |
| **Total lift** | **+33–62% vs. season-only GOI** |

### Slate GOI vs Season GOI

| Dimension | v1.0 Season GOI | v2.0 Slate GOI |
|-----------|-----------------|----------------|
| **Timeframe** | Full season | Last N games (5–10) |
| **Granularity** | Team vs. League | Team vs. Slate Opponents |
| **Context** | Static | Dynamic per slate |
| **Use Case** | General edge | Slate-specific stack prioritization |
| **Output** | Team rankings | Game prioritization + stack flags |

### Game Prioritization Logic (Stack Radar)

For each game on the slate:

```
GOI Diff = (Team A Last-5 GOI) - (Team B Last-5 GOI)
         + Venue Boost (if A home)
         + Rest Boost
         + PP% vs PK% mismatch

Prioritize games where:
- GOI Diff > 1.5 → Stack the favorite
- PP% > 30% and opp PK% < 70% → PP stack
- HDC% > 60% both sides → High-event game
```

### Example Output: 3-Game Slate

```
SLATE: Oct 27, 2025 — 3 Games
════════════════════════════════════════
PRIORITY 1 → FLA vs NJD
  FLA Last 5: CF% 59.1 | xGF 3.4 | HDC% 62% | Net Pen/60 +1.2
  NJD Last 5: CF% 48.3 | xGF 2.1 | HDC% 41%
  → GOI Diff: +2.1 | FLA PP% 33% vs NJD PK% 68%
  STACK: FLA Line 1 + D

PRIORITY 2 → COL vs CHI
  COL Last 5: xGF 3.1 | PP% 28%
  CHI Last 5: xGA 3.8 | PK% 72%
  → Mismatch alert

PRIORITY 3 → TOR vs NYR
  Even matchup, low edge
```

### Slate GOI Weighting Formula

```
Slate GOI = 0.4 × Last5_CF% 
          + 0.3 × Last5_xGF 
          + 0.2 × HDC% 
          + 0.1 × NetPen/60
```

Then cross-rank:
1. **Season GOI Rank** (baseline)
2. **Last 5-Game GOI Rank** (form)
3. **Slate GOI Rank** (weighted: 40% last 5, 30% matchup, 20% venue, 10% rest)

### Design Rationale & Assumptions

**Current Slate GOI Formula**:
```
Slate GOI = 0.4 × Last5_CF% 
          + 0.3 × Last5_xGF 
          + 0.2 × HDC% 
          + 0.1 × NetPen/60
```

**Weight Rationale** (based on DFS pro playbooks & GROK research):
- **40% Last 5 Games (Form)**: Form matters most in short samples. Hot/cold streaks are more predictive than season averages in 2–3 game slates. Research from DFS community suggests recent performance carries 40–50% weight.
- **30% Matchup (Opponent Quality)**: Opponent's xGA allowed, PK%, and defensive structure are critical for stack selection. Weak defense = higher scoring ceiling. Established in DFS literature as 25–35% weight.
- **20% Venue (Home/Road)**: Home teams have ~8% xGF advantage (rink familiarity, travel fatigue). Secondary but consistent factor. Typically 15–25% in pro models.
- **10% Rest (B2B Penalty)**: Back-to-back games reduce scoring by 3–7%. Real but tertiary factor. Often 5–15% in models.

**Assumptions to Validate with GROK** (Future Enhancement):
1. **Weight Optimization**: Is 40/30/20/10 optimal, or should it be 50/25/15/10? Requires backtesting against historical slates.
2. **Venue Boost**: Should venue boost be +8% xGF universally, or adjusted per team (e.g., Vegas +12%, Arizona +4%)?
3. **Rest Penalty**: Is -3–7% per 60 min accurate, or should it be more aggressive (-10–15%)?
4. **Missing Factors**: Should we add injury impact, Vegas line movement, or goalie matchup quality?

**Guardrails Rationale** (Applied Post-GOI):
- **Early-Season Caps (First 10 Games)**: Small sample volatility inflates shooting %, save %, and PP%. Caps prevent overweighting noise. Threshold of 10 games aligns with statistical significance research.
- **Hot Goalie Alert (SV% > 0.925)**: Regression to mean is strong. Goalies above 0.925 SV% over 3–5 games typically regress. Penalty of -0.7 on shot volume stats reflects expected regression.
- **Market Drift (Line Move > 15¢)**: Sharp money moving lines signals information. If underdog moves 15¢+ without statistical support (low z-score), fade entirely. Threshold of 15¢ is industry standard.

**Source & Validation**:
- Weights derived from DFS pro playbooks (Sleeper, Stokastic, Occupy Fantasy)
- GROK research on NHL parity and small-sample effects
- Guardrails based on regression analysis and market efficiency literature
- **Status**: Provisional. Requires backtesting against 20+ historical slates to optimize.

---

## GROK's 7 Enhancements (v2.0 Refinements)

**Context**: GROK reviewed the architecture and identified 7 targeted enhancements to improve accuracy, robustness, and production-readiness. These are not blockers — they are refinements that improve signal fidelity and code quality.

### Enhancement 1: High-Danger Zone Definition (Configurable)

**Current State**: Hardcoded in `get_game_detail.py`

**Recommendation**: Move to `utils/coordinate_utils.py` + config

**Implementation**:
```python
# config/config.yaml
high_danger_zone:
  x_threshold: 15  # feet from net
  y_threshold: 8.5  # feet from center (goal posts)
  net_x: 89  # net position in NHL coordinates

# utils/coordinate_utils.py
def is_high_danger(x: float, y: float, config: Dict) -> bool:
    """Check if shot is in high-danger zone."""
    x_dist = abs(x) - config['high_danger_zone']['net_x']
    y_dist = abs(y)
    return (x_dist < config['high_danger_zone']['x_threshold'] and 
            y_dist < config['high_danger_zone']['y_threshold'])
```

**Why**: Allows tuning zone thresholds without code changes. Future models can adjust zone size.

---

### Enhancement 2: xG Model (v1.0 Simple + v2.1 Upgrade Path)

**v1.0 (Current — Ship Now)**:
```python
# utils/xg_calculator.py
def calculate_xg(x: float, y: float, shot_type: str = "Wrist") -> float:
    """Simple distance-based xG model (v1.0)."""
    distance = math.sqrt((abs(x) - 89) ** 2 + y ** 2)
    
    if distance < 15:
        return 0.22 if shot_type != "Slap" else 0.17
    elif distance < 30:
        return 0.10 if shot_type != "Slap" else 0.08
    else:
        return 0.04 if shot_type != "Slap" else 0.03
```

**Rationale**:
- Distance is the dominant xG factor (~70–80% of signal)
- Shot type adds ~10% accuracy
- Rebound/rush flags add marginal value
- **v1.0 is 1 day to implement, 90% of value**

**v2.1 Upgrade Path (Documented, Not Implemented)**:
```yaml
# config/xg_model.yaml
version: 2.1
features:
  shot_type_weights: true
  rebound_detection: true
  strength_adjustment: true
  angle_factor: true
  
# TODO: Implement in v2.1
# - Add rebound flag detection (previous event type)
# - Add strength state weighting (5v5 vs PP)
# - Add angle factor (shot angle from net)
```

**Why**: Balances speed (v1.0) with accuracy (v2.1 path). No breaking changes.

---

### Enhancement 3: Strength State Filtering (5v5 vs PP)

**Current State**: All situations included

**Recommendation**: Add strength state filter to Corsi, xG, and penalty stats

**Implementation**:
```python
# stats_calculator.py
def calculate_cf_5v5(play_by_play: Dict, team_id: int) -> float:
    """Corsi For % at 5v5 only."""
    events = [
        e for e in play_by_play['plays']
        if e.get('situationCode', '').startswith('5')  # 5v5 only
        and e.get('team', {}).get('id') == team_id
    ]
    # ... calculate CF% from filtered events
```

**Why**: 5v5 Corsi is more predictive than all-situations. PP/PK stats are separate metrics.

---

### Enhancement 4: TOI Normalization (From Boxscore)

**Current State**: Missing in penalty/60 calculations

**Recommendation**: Extract TOI from boxscore, use for normalization

**Implementation**:
```python
# data_parser.py
def extract_team_toi(boxscore: Dict, team_id: int) -> float:
    """Extract total team TOI in minutes from boxscore."""
    players = boxscore['playerByGameStats']
    toi_list = [
        p['toi'] for p in players
        if p.get('team', {}).get('id') == team_id
    ]
    return sum(toi_list) / 60  # Convert seconds to minutes

# stats_calculator.py
def calculate_pen_taken_60(play_by_play: Dict, team_id: int, toi_minutes: float) -> float:
    """Penalties Taken per 60 minutes."""
    penalties = len([e for e in play_by_play['plays'] 
                     if e.get('typeDescKey') == 'penalty'
                     and e.get('details', {}).get('eventOwnerTeamId') == team_id])
    return (penalties / toi_minutes) * 60 if toi_minutes > 0 else 0
```

**Why**: Normalizes penalty stats to 60-minute scale (standard in hockey analytics).

---

### Enhancement 5: Game State Filtering (Situational Code)

**Current State**: All situations included

**Recommendation**: Add `situationCode` filtering for context-specific stats

**Implementation**:
```python
# stats_calculator.py
SITUATION_CODES = {
    '5v5': '5',      # Even strength
    'PP': '4',       # Power play (team advantage)
    'PK': '3',       # Penalty kill (team disadvantage)
    'OT': 'O',       # Overtime
}

def calculate_cf_by_situation(play_by_play: Dict, team_id: int, situation: str) -> float:
    """Corsi For % by game situation."""
    situation_code = SITUATION_CODES.get(situation)
    events = [
        e for e in play_by_play['plays']
        if e.get('situationCode', '').startswith(situation_code)
        and e.get('team', {}).get('id') == team_id
    ]
    # ... calculate CF% from filtered events
```

**Why**: Allows separate analysis of even-strength vs. special teams performance.

---

### Enhancement 6: Cache Strategy (TTL + Size Limits)

**Current State**: File-based JSON (no expiry)

**Recommendation**: Add TTL (time-to-live) + size limits to cache

**Implementation**:
```python
# config/config.yaml
cache:
  ttl_seconds: 86400  # 24 hours
  max_size_mb: 500
  cleanup_interval_hours: 6

# api_client.py
def _is_cache_valid(cache_file: Path, ttl_seconds: int) -> bool:
    """Check if cached file is still valid."""
    if not cache_file.exists():
        return False
    age_seconds = time.time() - cache_file.stat().st_mtime
    return age_seconds < ttl_seconds

def _enforce_cache_size(cache_dir: Path, max_size_mb: int) -> None:
    """Remove oldest files if cache exceeds size limit."""
    total_size = sum(f.stat().st_size for f in cache_dir.glob('*.json'))
    if total_size > max_size_mb * 1024 * 1024:
        # Remove oldest files
        for f in sorted(cache_dir.glob('*.json'), key=lambda x: x.stat().st_mtime):
            f.unlink()
            if sum(f.stat().st_size for f in cache_dir.glob('*.json')) < max_size_mb * 1024 * 1024:
                break
```

**Why**: Prevents stale cache data and unbounded disk usage.

---

### Enhancement 7: Logging Strategy (Logging Module, Not Print)

**Current State**: `print()` statements throughout `get_game_detail.py`

**Recommendation**: Use Python `logging` module with levels

**Implementation**:
```python
# config/logging_config.yaml
version: 1
formatters:
  standard:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: standard
  file:
    class: logging.FileHandler
    filename: logs/app.log
    level: INFO
    formatter: standard
loggers:
  api_client:
    level: DEBUG
    handlers: [console, file]
  stats_calculator:
    level: INFO
    handlers: [console, file]

# Every module
import logging
logger = logging.getLogger(__name__)

# Replace: print(f"Fetching game {game_id}")
# With: logger.info(f"Fetching game {game_id}")

# Replace: print(f"ERROR: {error}")
# With: logger.error(f"ERROR: {error}", exc_info=True)
```

**Why**: Enables log level control, file output, and structured debugging.

---

### Implementation Priority for Enhancements

| Enhancement | Priority | Effort | Impact | Phase |
|---|---|---|---|---|
| 1. High-Danger Config | HIGH | 1 day | High (enables tuning) | Phase 2 |
| 2. xG Model v1.0 | HIGH | 1 day | High (core stat) | Phase 2 |
| 3. Strength Filtering | MEDIUM | 2 days | Medium (context) | Phase 3 |
| 4. TOI Normalization | HIGH | 1 day | High (accuracy) | Phase 2 |
| 5. Game State Filter | MEDIUM | 1 day | Medium (analysis) | Phase 3 |
| 6. Cache Strategy | LOW | 1 day | Low (ops) | Phase 1 |
| 7. Logging Strategy | MEDIUM | 1 day | Medium (debugging) | Phase 1 |

---

### Collaborative Development Model: You, Me, and GROK

**Context for Future AI Assistants**:

This project operates on a **three-party collaboration model**:

1. **You (Developer)**: Direct context, decision-making, domain intuition, and project vision
2. **Me (Cascade AI)**: Direct dialog with you, code implementation, architecture design, documentation, and system integration
3. **GROK (Domain Expert)**: Subject matter expertise in DFS analytics, NHL statistics, and advanced modeling

**Why This Model Exists**:

- **Cascade's Strength**: I have continuous dialog with you, understand project context deeply, can implement code, and maintain architectural coherence across all modules and documentation.
- **Cascade's Limitation**: I lack specialized domain expertise in DFS analytics, NHL parity, and advanced statistical modeling that requires years of professional experience.
- **GROK's Strength**: Deep domain knowledge in DFS strategy, NHL analytics, statistical methods, and professional playbook patterns.
- **GROK's Limitation**: No direct dialog with you; operates in isolation without project context.

**How It Works**:

1. **You bring GROK insights to me** (e.g., "GROK says use confidence weights for early-season volatility")
2. **I integrate GROK's domain logic into code and documentation** (e.g., implement the confidence weight formula, explain the rationale)
3. **I maintain context continuity** (e.g., ensure GROK's recommendation aligns with architecture, other modules, and design decisions)
4. **You validate the integration** (e.g., "Does this match what GROK intended?")

**Practical Example**:

- GROK provides: "Use z-score threshold for opponent quality: PK% < -0.5σ = weak"
- You bring it to me: "GROK says to flag weak defenses this way"
- I implement: Add to `slate_goi_calculator.py`, document in config, explain in architecture doc
- You validate: "Yes, that's what GROK meant"

**What This Means for Future AI Assistants**:

When you see references to GROK in this codebase:
- **It's not a mistake or external dependency** — it's intentional collaboration
- **GROK's recommendations are domain-validated** — trust them as subject matter expertise
- **Your job is to implement and integrate** — not to second-guess the domain logic
- **Maintain the dialog loop** — if GROK's recommendation seems unclear, ask the developer to clarify with GROK
- **Document the source** — always note when code/logic comes from GROK research

**Key Principle**:

> **You (Cascade) are the architect and implementer. GROK is the domain validator. The developer is the integrator and decision-maker.**

This model ensures:
- ✅ Domain accuracy (GROK validates)
- ✅ Code quality (Cascade implements)
- ✅ Project coherence (Developer integrates)
- ✅ Continuous improvement (All three parties iterate)

**When You Reference GROK**:

Future AI assistants should expect to see:
- "GROK recommends..." (domain expertise)
- "GROK validated..." (confirmation of approach)
- "GROK suggests..." (alternative approaches)
- "Per GROK research..." (citation of domain findings)

**This is not a limitation — it's a strength.** You have access to both architectural rigor (me) and domain expertise (GROK) in one project.

---

## TPI Evolution: From Manual Input to Automatic Byproduct

**Core Question**: Do we still need TPI in v2.0, or did it become obsolete with game-level data?

**Answer**: **YES — TPI is still essential, but its role fundamentally changes.**

### The Conceptual Shift

| Aspect | v1.0 (Current) | v2.0 (Proposed) |
|--------|---|---|
| **TPI Source** | Manual Excel files (weekly) | Automated from game-level data (nightly) |
| **TPI Role** | Required input to GOI | Automatic byproduct of aggregation |
| **Data Freshness** | Stale (updated weekly) | Always current (updated nightly) |
| **Dependency** | Manual merge required | Zero-touch automation |
| **Reliability** | Manual error risk | Derived from raw API data |

### Why TPI Cannot Be Eliminated

**Z-scores require league context.** Consider this example:

| Team | CF% | League Avg | League SD | Z-Score | Interpretation |
|------|-----|-----------|-----------|---------|-----------------|
| FLA | 55% | 50% | 3% | +1.67σ | Elite (top 5%) |
| NJD | 52% | 50% | 3% | +0.67σ | Above average |

**Without league context**, raw stats are meaningless. "Is 55% CF% good?" Only makes sense when compared to the entire league.

**TPI is the normalization layer** that provides this context.

### The Refactored Data Flow

**v1.0 Flow**:
```
[Manual TPI Spreadsheet]
        ↓
[Import into GOI Model]
        ↓
[Output GOI Rankings]
```

**v2.0 Flow**:
```
[Game-Level Data (API)]
        ↓
[Aggregate: Season 13 Stats + Last X 13 Stats per Team]
        ↓
[Compute League-Wide: Mean & SD for each stat]
        ↓
[Z-Score Every Team (Season + Last X)] ← TPI emerges here
        ↓
[Calculate GOI = f(Season Z, Last X Z, Matchup, Venue)]
        ↓
[Output: TPI Rankings + GOI Rankings]
```

### The GOI v2 Formula (Refined)

```
GOI = 0.4 × Z_Season(13_stats) 
    + 0.5 × Z_LastX(13_stats) 
    + 0.1 × Context_Score
```

Where:
- **Z_Season** = Average z-score of 13 stats (season-to-date)
- **Z_LastX** = Average z-score of 13 stats (last X games)
- **Context_Score** = Venue boost + Rest penalty + Matchup adjustment

### Critical Operational Decisions

**These decisions directly impact implementation and must be made before coding:**

#### **Decision 1: Z-Score Computation Timing**

**Question**: When do you recompute z-scores?

**Options**:
- **Nightly**: Recompute all 32 teams' z-scores after each day's games
  - **Pros**: Most accurate, always current
  - **Cons**: Expensive (32 teams × 13 stats × 2 windows per night)
  - **Recommended for**: Daily slate generation
  
- **Weekly**: Recompute every Sunday (or after each week)
  - **Pros**: Cheaper, stable rankings
  - **Cons**: Stale data (z-scores from 3 days old by Friday)
  - **Recommended for**: Season-long tracking
  
- **Per-Slate**: Compute z-scores only when generating a slate report
  - **Pros**: Minimal computation
  - **Cons**: Biased (z-scores relative to slate teams, not league)
  - **NOT RECOMMENDED**: Violates statistical integrity

**Current Recommendation**: **Nightly** (most accurate for DFS use case)

#### **Decision 2: Last X Games Window Definition**

**Question**: What is X?

**Options**:
- **X = 5 games** (hardcoded)
  - **Pros**: Very reactive (captures hot/cold streaks)
  - **Cons**: Noisy (small sample, high variance)
  - **Use case**: Slate-specific form detection
  
- **X = 10 games** (hardcoded)
  - **Pros**: Balanced (2–3 weeks of data, ~20 games per team)
  - **Cons**: Less reactive to recent changes
  - **Use case**: General form tracking
  
- **X = Last 7 calendar days** (dynamic)
  - **Pros**: Calendar-aligned (weekly form)
  - **Cons**: Variable game count (3–5 games depending on schedule)
  - **Use case**: Weekly trend analysis
  
- **X = Dynamic** (e.g., "last 10 games or 14 days, whichever is more")
  - **Pros**: Robust (adapts to schedule)
  - **Cons**: Complex logic
  - **Use case**: Flexible form detection

**Current Recommendation**: **X = 5 games** (optimal for 2–3 game slate prioritization)

#### **Decision 3: Early-Season Volatility Handling**

**Question**: How do you handle early-season noise (first 10 games)?

**Options**:
- **Cap z-scores** (e.g., max z-score = ±1.5σ for first 10 games)
  - **Pros**: Prevents extreme outliers
  - **Cons**: Artificially dampens signal
  
- **Cap GOI directly** (e.g., max GOI = 0.8 for first 10 games)
  - **Pros**: Prevents extreme stack recommendations
  - **Cons**: Less transparent
  
- **Apply confidence weights** (e.g., weight = min(games_played / 10, 1.0))
  - **Pros**: Gradual transition from noisy to stable
  - **Cons**: More complex
  
- **Use rolling window** (e.g., z-score vs. last 30 games, not full season)
  - **Pros**: Naturally dampens early-season noise
  - **Cons**: Loses season-long context

**Current Recommendation**: **Apply confidence weights** (gradual transition, most statistically sound)

#### **Decision 4: Opponent Quality Calculation**

**Question**: How do you define "bad PK" or "weak defense"?

**Options**:
- **Season PK%**: Use opponent's full-season PK%
  - **Pros**: Stable, representative
  - **Cons**: Doesn't reflect recent form
  
- **Last 5-Game PK%**: Use opponent's recent PK%
  - **Pros**: Reflects current state
  - **Cons**: Noisy (small sample)
  
- **Z-Score Threshold**: Flag if opponent PK% < -1σ
  - **Pros**: Statistically principled
  - **Cons**: Requires league context (see Decision 1)
  
- **Hybrid**: Season PK% + Last 5-Game trend
  - **Pros**: Balanced
  - **Cons**: More complex

**Current Recommendation**: **Z-Score Threshold** (PK% < -0.5σ = "weak", < -1.5σ = "very weak")

### Implementation Implications

**These decisions affect module design**:

| Module | Affected By | Decision |
|--------|-------------|----------|
| `aggregator.py` | Decision 2 (Last X window) | Must maintain rolling 5-game windows |
| `zscore_calculator.py` | Decision 1 (Timing) | Must compute nightly for all 32 teams |
| `guardrails.py` | Decision 3 (Early-season) | Must apply confidence weights |
| `slate_goi_calculator.py` | Decision 4 (Opponent quality) | Must lookup opponent z-scores |

### Summary: TPI in v2.0

**TPI didn't disappear — it evolved:**
- **v1.0**: Manual input (spreadsheet) → Prerequisite for GOI
- **v2.0**: Automatic output (from game data) → Byproduct of aggregation

**The win**: 
- No more manual TPI updates
- Always-current rankings
- Transparent derivation (from raw API data)
- Enables nightly slate GOI generation

**The requirement**:
- Must compute z-scores league-wide (all 32 teams)
- Must maintain rolling windows (season + last X)
- Must handle early-season volatility
- Must define opponent quality metrics

---

## Integration with GOI v1.0 Model

**Context**: This v2.0 architecture builds on proven v1.0 DFS analytics logic. The v1.0 model successfully implemented z-score normalization, bucketing, TPI, and GOI calculations for team-level season stats. v2.0 enhances this by automating data collection (API-driven) and providing game-level granularity instead of manual Excel input. **Critically, v2.0 adds slate-specific context** (form, matchup, venue, rest) to transform season GOI into actionable stack prioritization.

### What We Reuse from v1.0

#### **Z-Score & Directional Adjustment Logic**
- **Source**: `calc_zscores_v2a.py` (v1.0)
- **Reuse**: Z-score calculation formula, directional reversal for "lower is better" stats
- **Adaptation**: Apply to game-level stats instead of season-level
- **New Module**: `zscore_calculator.py`
- **Key Functions**:
  - `calculate_zscore(value, mean, std_dev)` → standardize stat to common scale
  - `apply_directional_adjustment(zscore, reverse_sign)` → flip sign for defensive/discipline stats

#### **Bucketing & TPI Calculation**
- **Source**: `calc_zscores_v2a.py` bucketing logic
- **Reuse**: Bucket definitions (Offensive Creation, Defensive Resistance, Pace Drivers), weighted averaging
- **Adaptation**: Aggregate z-scores per bucket, apply bucket weights (0.4, 0.3, 0.3)
- **New Module**: `tpi_calculator.py`
- **Key Functions**:
  - `bucket_stats(stats_dict, config)` → group z-scores by bucket
  - `calculate_tpi(bucket_averages, bucket_weights)` → weighted sum

#### **GOI Calculation**
- **Source**: `calculate_goi.py` (v1.0)
- **Reuse**: GOI formula (0.6 × offensive mismatch + 0.4 × pace), ranking logic
- **Adaptation**: Input TPI from our calculator instead of CSV file
- **New Module**: `goi_calculator.py`
- **Key Functions**:
  - `calculate_matchup_opportunity(home_tpi, away_tpi)` → offensive mismatch
  - `calculate_game_pace(home_pace, away_pace)` → average pace drivers
  - `calculate_goi(home_opp, away_opp, game_pace)` → per-team GOI

#### **Guardrails & Adjustments**
- **Source**: `apply_goi_guardrails()` function (v1.0)
- **Reuse**: Early-season volatility caps, hot goalie alerts, market drift logic
- **Adaptation**: Apply to game-level stats with appropriate thresholds
- **New Module**: `guardrails.py` (optional, can be in `goi_calculator.py`)
- **Key Guardrails**:
  - Early-season caps (first 10 games): Cap shooting %, save %, PP% volatility
  - Hot Goalie Alert: Penalize shot volume vs. hot goalies (SV% > 0.925)
  - Market Drift: Fade underdog moves without statistical support

#### **Configuration Structure**
- **Source**: `config_v2.yaml` (v1.0)
- **Reuse**: Stat definitions (name, weight, bucket, sort_order, reverse_sign), bucket weights
- **Adaptation**: Update stat names to match our 13 game-level stats
- **New Config Sections**:
  ```yaml
  stats:
    - name: CF%
      weight: 1
      bucket: pace_drivers
      sort_order: desc
      reverse_sign: false
    - name: xGF
      weight: 1
      bucket: offensive_creation
      sort_order: desc
      reverse_sign: false
    # ... 11 more stats
  
  bucket_weights:
    offensive_creation: 0.4
    defensive_resistance: 0.3
    pace_drivers: 0.3
  
  goi_parameters:
    alpha: 0.3                    # Disparity weighting (0.3-0.5)
    offense_weight: 0.6           # vs. pace in GOI
    pace_weight: 0.4
  
  guardrails:
    early_season_games: 10
    hot_goalie_sv_threshold: 0.925
    market_drift_threshold: 0.15
  ```

### What We DON'T Reuse from v1.0

| Component | Why Not | v2.0 Alternative |
|-----------|---------|------------------|
| Manual Excel loading | Data source is now NHL API | `api_client.py` + `db_manager.py` |
| Team name mapping from Excel | Team IDs come from API | Direct ID matching in `data_parser.py` |
| Main orchestration (`main.py`) | Designed for manual workflow | Modular `orchestrator.py` + `get_game_detail.py` |
| Static season-level aggregation | Need dynamic game-level aggregation | `aggregator.py` with rolling windows |

### Data Flow: v1.0 vs v2.0

**v1.0 (Manual)**:
```
Excel (manual entry)
    ↓
calc_zscores_v2a.py (z-scores)
    ↓
calculate_goi.py (GOI)
    ↓
Output: zOverall.csv, team_total_zscores.csv, goi_rankings.csv
```

**v2.0 (Automated)**:
```
NHL API (boxscore + play-by-play)
    ↓
api_client.py + data_parser.py (fetch & parse)
    ↓
stats_calculator.py (13 stats per game)
    ↓
db_manager.py (store in SQLite)
    ↓
aggregator.py (roll up to team/date)
    ↓
zscore_calculator.py (z-scores)
    ↓
tpi_calculator.py (TPI)
    ↓
goi_calculator.py (GOI)
    ↓
guardrails.py (apply adjustments)
    ↓
Output: game_stats.csv, team_aggregates.csv, tpi_rankings.csv, goi_rankings.csv
```

### Implementation Notes for Future AI Assistants

**When implementing `zscore_calculator.py`**:
- Reference v1.0 `calc_zscores_v2a.py` for z-score formula
- Ensure directional adjustment flips sign for: xGA, PK%, Pen Taken/60
- Test with known v1.0 outputs to validate formula

**When implementing `tpi_calculator.py`**:
- Bucket weights must sum to 1.0 (0.4 + 0.3 + 0.3 = 1.0)
- Verify bucketing matches config (stat → bucket mapping)
- Normalize TPI across all teams on slate (another z-score layer)

**When implementing `goi_calculator.py`**:
- GOI formula: `0.6 × offensive_mismatch + 0.4 × game_pace`
- Offensive mismatch = opponent's defensive z-avg - team's defensive z-avg
- Higher GOI = better stacking opportunity (more scoring potential)

**When implementing `guardrails.py`**:
- Early-season caps apply only to first 10 games per team
- Hot goalie penalty (-0.7) applies to shot volume stats only
- Market drift requires both: underdog status AND statistical weakness

### Testing Against v1.0

To validate v2.0 outputs:
1. Run v2.0 on a historical slate (e.g., Oct 7-18, 2025)
2. Compare TPI rankings to v1.0 season-level rankings (should be directionally similar)
3. Compare GOI rankings to v1.0 goi_rankings.csv (should match if using same teams/dates)
4. Backtest both models against actual DFS outcomes (ROI analysis)

---

**Document Version**: 1.2  
**Status**: Ready for Implementation (GROK-Validated)  
**Author**: Cascade AI Assistant  
**Reviewed By**: GROK (Domain Expert)  
**Last Updated**: October 28, 2025  
**Integration Notes**: v1.0 GOI model reference included; v2.0 builds on proven logic with API-driven automation; GROK's 7 enhancements integrated for production-readiness
