# Directory Structure

## Root Organization

```
NHLGameLogs/
├── src/                          # Source code (main application)
│   ├── orchestrator/             # Data orchestration pipeline
│   │   ├── __init__.py
│   │   ├── assessment.py         # Assess unfetched games
│   │   ├── fetcher_and_aggregator.py  # Fetch games + aggregate stats
│   │   ├── raw_extractor.py      # Extract raw stats from API
│   │   └── validator.py          # Validate extracted stats
│   └── ...
│
├── docs/                         # Documentation
│   ├── DESIGN_DECISION_PP_STATS.md  # Design decisions (PP stats)
│   ├── architecture_design_decisions.md
│   └── ...
│
├── scripts/                      # Main entry points
│   └── run_fetch.py             # Fetch and aggregate games for a team
│
├── tools/                        # Debugging & utility scripts
│   ├── debug_boxscore.py        # Debug NHL API boxscore structure
│   ├── debug_pp.py              # Debug PP extraction
│   ├── debug_pp_boxscore.py     # Debug PP in boxscore
│   ├── check_pp_stats.py        # Check PP stats in database
│   ├── clear_tables.py          # Clear database tables
│   └── dump_game.py             # Dump game stats vertically
│
├── tests/                        # Test scripts
│   ├── test_extraction.py       # Test raw extraction logic
│   └── test_stats_api.py        # Test Stats API connectivity
│
├── Data/                         # Database & data files
│   ├── test_nhl_stats.db        # SQLite database
│   └── schedule.csv             # NHL schedule
│
├── db_setup/                     # Database initialization
│   └── schema.sql               # Database schema
│
├── config/                       # Configuration files
│
├── Archive/                      # Old/archived files
│
├── _GOI_v1.0/                    # Previous GOI implementation
│
├── README.md                     # Main documentation
├── USAGE_GUIDE.md               # How to use the pipeline
├── PROJECT_SUMMARY.md           # Project overview
├── BACKLOG.md                   # Future work & known issues
├── GROK_PP_STATS.md             # Grok consultation on PP stats
└── DIRECTORY_STRUCTURE.md       # This file
```

---

## Key Directories

### `src/orchestrator/`
**Purpose**: Core data extraction and aggregation pipeline

**Key files**:
- `assessment.py` - Assess which games need fetching
- `fetcher_and_aggregator.py` - Fetch from NHL API + update database
- `raw_extractor.py` - Extract raw stats (Corsi, xG, PP, faceoffs)
- `validator.py` - Validate extracted stats against external sources

### `scripts/`
**Purpose**: Main entry points for running the pipeline

**Usage**:
```bash
python scripts/run_fetch.py FLA  # Fetch all unfetched FLA games
```

### `tools/`
**Purpose**: Debugging and utility scripts (not part of main pipeline)

**Examples**:
- `dump_game.py` - Inspect game stats vertically
- `debug_pp.py` - Debug PP extraction logic
- `clear_tables.py` - Reset database for re-fetching

### `tests/`
**Purpose**: Test scripts for validation

**Examples**:
- `test_extraction.py` - Test raw extraction on a sample game
- `test_stats_api.py` - Test Stats API connectivity

### `docs/`
**Purpose**: Design decisions and architecture documentation

**Key files**:
- `DESIGN_DECISION_PP_STATS.md` - Why we chose Stats API for PP stats
- `architecture_design_decisions.md` - Overall architecture decisions

---

## Usage

### Running the Pipeline
```bash
# Fetch and aggregate all unfetched games for FLA
python scripts/run_fetch.py FLA
```

### Debugging
```bash
# Inspect a specific game's stats
python tools/dump_game.py 2025020027

# Debug PP extraction
python tools/debug_pp.py

# Check PP stats in database
python tools/check_pp_stats.py
```

### Testing
```bash
# Test extraction logic
python tests/test_extraction.py

# Test Stats API
python tests/test_stats_api.py
```

---

## Database

**Location**: `Data/test_nhl_stats.db`

**Tables**:
- `team_game_stats` - Raw stats per team per game
- `team_aggregates` - Season totals per team

**Schema**: See `db_setup/schema.sql`

---

## Configuration

**Schedule**: `Data/schedule.csv` (NHL game schedule)

**Database path**: Configured in `scripts/run_fetch.py`

---

## Notes

- **Debug scripts** in `tools/` are for development only
- **Test scripts** in `tests/` validate extraction logic
- **Main pipeline** is in `src/orchestrator/`
- **Entry point** is `scripts/run_fetch.py`

---

## Future Phases

- **Phase 2**: Error handling & idempotency (see `BACKLOG.md`)
- **Phase 3**: Z-scores, TPI, GOI calculation
- **Phase 4**: Slate optimization & stacking

See `BACKLOG.md` for details.
