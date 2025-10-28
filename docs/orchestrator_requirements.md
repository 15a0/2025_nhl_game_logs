# NHL Game Logs Orchestrator - Requirements & Plan

**Document Purpose**: Define requirements, architecture, and next steps for building an orchestrator that scales `get_game_detail.py` to process multiple games intelligently.

**Audience**: Developer (you), future AI assistants, external AI for second opinions  
**Status**: Planning Phase (no code yet)  
**Last Updated**: October 27, 2025

---

## Table of Contents

1. [Context Recap](#context-recap)
2. [Requirements](#requirements)
3. [Architecture Overview](#architecture-overview)
4. [Next Steps (Plan)](#next-steps-plan)
5. [Key Design Decisions](#key-design-decisions)
6. [Questions for Review](#questions-for-review)
7. [Documentation Artifacts](#documentation-artifacts)

---

## Context Recap

### Current State

- **`get_game_detail.py`**: Working prototype that fetches boxscore + play-by-play data for a **single game** and calculates advanced stats
- **Output**: Currently exports to CSV; moving to SQLite
- **Goal**: Scale to process multiple games intelligently without manual intervention

### Key Conversation Points

1. **DB Schema**: Two-row-per-game approach (one row per team per game) for easy team-based queries
2. **SQLite DB**: `nhl_stats.db` with `games` and `game_stats` tables
3. **Avoid Re-processing**: Check if game already analyzed before running API calls
4. **Filter Future Games**: Only process games with `gameState = "OFF"` (not "FUT")
5. **Flexible Input**: Accept game ID, team abbreviation, or date range

---

## Requirements

### Functional Requirements

#### FR1: Input Flexibility

The orchestrator must accept multiple input types:

- **Single Game ID**: `2025020001` → Process one game
- **Team Abbreviation**: `FLA` → Find all games where FLA played (home or away)
- **Date Range**: `2025-10-07` to `2025-10-31` → Find all games in that range
- **All Completed Games**: `--all` → Process entire season

#### FR2: Smart Processing

The orchestrator must:

1. Query `schedule.csv` or `games` table to find matching games
2. Filter: Only process games with `game_state = "OFF"` (not "FUT")
3. Check if game already in `game_stats` table → **skip if exists**
4. Run `get_game_detail.py` for each new game
5. Insert results into SQLite `game_stats` table (not CSV)

#### FR3: Data Integrity

- Prevent duplicate processing (leverage `UNIQUE(game_id, team)` constraint)
- Handle API failures gracefully (retry logic or skip with logging)
- Track which games were processed, skipped, or failed
- Log all operations for debugging

#### FR4: Query Capabilities

- Calculate aggregated stats for a team (e.g., season average Corsi, xG)
- Filter by date range
- Compare home vs away performance
- Export results (CSV, JSON, or direct DB query)

### Non-Functional Requirements

#### NFR1: Preserve Prototype

- Keep `get_game_detail.py` **unchanged** (it's the "gold version")
- Orchestrator calls it as a subprocess or imports its functions
- **No modifications** to stat calculation logic

#### NFR2: Maintainability

- Code must be readable for future AI assistants
- Document API field mappings (reference: `api_reference.md`)
- Clear separation of concerns: fetch → process → store → query
- Include docstrings and comments

#### NFR3: Performance

- Avoid re-processing games (DB lookup before API call)
- Batch processing for teams with many games
- Optional: Rate limiting for NHL API (0.5-1 sec between requests to be respectful)

#### NFR4: Scalability

- Design should support future enhancements (e.g., parallel processing, scheduling)
- DB schema should handle multiple seasons

---

## Architecture Overview

```
orchestrator.py (main entry point)
│
├── Input Handler
│   ├── Parse game ID / team / date range / "all"
│   └── Validate input
│
├── Schedule Manager
│   ├── Load schedule from CSV or DB
│   ├── Filter by game_state = "OFF"
│   └── Find matching games (by ID, team, date)
│
├── Processing Engine
│   ├── Check if game already processed (DB lookup)
│   ├── Call get_game_detail.py for new games
│   ├── Parse results
│   ├── Insert stats into game_stats table
│   └── Handle errors/logging
│
└── Query Engine
    ├── Aggregate stats by team/date
    ├── Export results
    └── Provide analytics
```

### Data Flow

```
User Input (game_id / team / date)
    ↓
Input Validation
    ↓
Query Schedule (CSV or DB)
    ↓
Filter: game_state = "OFF"
    ↓
For each matching game:
    ├─ Check: Game in game_stats table?
    │   ├─ Yes → Skip (log as "already processed")
    │   └─ No → Continue
    ├─ Call get_game_detail.py
    ├─ Parse results
    └─ Insert into game_stats table
    ↓
Log Summary (processed, skipped, failed)
```

---

## Next Steps (Plan)

### Phase 1: Orchestrator Core (Foundation)

**Goal**: Build the core orchestrator that can process games and store results in DB.

#### Step 1.1: Create `orchestrator.py`
- Main entry point with argument parsing
- Support: `--game-id`, `--team`, `--date-start`, `--date-end`, `--all`
- Input validation (e.g., valid team abbreviations, date formats)

#### Step 1.2: Implement Schedule Manager
- Load `schedule.csv` into `games` table (one-time or on-demand)
- Query games by ID / team / date range
- Filter for `game_state = "OFF"`
- Return list of games to process

#### Step 1.3: Implement Processing Engine
- Check if game already in `game_stats` table
- Call `get_game_detail.py` (as subprocess or function import)
- Parse results and insert into DB
- Log successes/failures/skips

#### Step 1.4: Testing
- Test with single game ID (e.g., 2025020001)
- Test with team (e.g., "FLA" → should find all FLA games)
- Test with date range (e.g., 2025-10-07 to 2025-10-31)
- Test with "all" flag
- Verify DB inserts are correct
- Verify deduplication (run twice, second run should skip all)

---

### Phase 2: Query & Analytics (Reporting)

**Goal**: Enable querying and analyzing stats from the DB.

#### Step 2.1: Create `query_stats.py`
- Query aggregated stats (team season avg, home/away split, etc.)
- Export to CSV/JSON
- Example queries:
  - "FLA season average Corsi"
  - "FLA home vs away comparison"
  - "Top 5 teams by xGF"

#### Step 2.2: Create `stats_analyzer.py`
- Calculate trends (e.g., Corsi over time)
- Compare teams
- Generate reports

---

### Phase 3: Configuration & Automation (Optional)

**Goal**: Support batch jobs and scheduling.

#### Step 3.1: YAML Config Support
- `config/process.yaml` for batch jobs
- Define multiple queries to run automatically
- Example:
  ```yaml
  jobs:
    - name: "FLA Season"
      team: "FLA"
    - name: "October Games"
      date_start: "2025-10-01"
      date_end: "2025-10-31"
  ```

#### Step 3.2: Scheduling (Future)
- Run orchestrator on a schedule (e.g., daily for new games)
- Integrate with task scheduler or cron

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Keep `get_game_detail.py` unchanged | It's proven; orchestrator wraps it |
| Use SQLite instead of CSV | Easier querying, no file management, scalable |
| Two-row-per-game schema | Matches your workflow; easy team-based queries |
| Check DB before API call | Avoid redundant processing; respect API limits |
| Filter `game_state = "OFF"` | Future games have no play-by-play data |
| Subprocess call to `get_game_detail.py` | Isolation; easy to debug; can run in parallel later |
| Separate orchestrator from stats calculation | Single responsibility; easier to maintain |

---

## Questions for Review

### Q1: Input Method
**Options**:
- **A**: CLI arguments (e.g., `python orchestrator.py --team FLA`)
- **B**: YAML config file (e.g., `config/process.yaml`)
- **C**: Both (CLI for ad-hoc, YAML for batch)

**Recommendation**: Start with CLI (simpler), add YAML later if needed.

---

### Q2: Schedule Source
**Options**:
- **A**: Load `schedule.csv` into `games` table once (on first run)
- **B**: Query `schedule.csv` each time
- **C**: Always fetch fresh from NHL API

**Recommendation**: Option A (load once, then use DB). Faster and avoids re-fetching.

---

### Q3: Logging
**Options**:
- **A**: Print to console only
- **B**: Log to file (e.g., `logs/orchestrator.log`)
- **C**: Both console and file

**Recommendation**: Option C (both). Helpful for debugging and auditing.

---

### Q4: Error Handling
**Options**:
- **A**: If one game fails, stop immediately
- **B**: If one game fails, continue with others (log the failure)
- **C**: Retry failed games N times before giving up

**Recommendation**: Option B (continue with others, log failures). More robust.

---

### Q5: Batch Size Limit
**Options**:
- **A**: No limit (process all matching games)
- **B**: Limit to N games per run (e.g., 50)
- **C**: User-configurable limit

**Recommendation**: Option A for now. Add limit later if API rate-limiting becomes an issue.

---

## Documentation Artifacts

### Already Created
- ✅ `docs/api_reference.md` - API structures, field mappings, calculations
- ✅ `db_setup/schema.sql` - DB schema (games, game_stats tables)
- ✅ `db_setup/init_db.py` - DB initialization script
- ✅ `.gitignore` - Excludes `*.db` files

### To Create (Phase 1)
- `docs/orchestrator_design.md` - Detailed architecture and design decisions
- `docs/orchestrator_usage.md` - How to use the orchestrator (examples)
- `README.md` - Project overview, setup instructions, quick start

### To Create (Phase 2+)
- `docs/query_guide.md` - How to query stats from the DB
- `docs/troubleshooting.md` - Common issues and solutions

---

## Summary

### What We're Building
An intelligent orchestrator that:
- Wraps `get_game_detail.py` (unchanged)
- Accepts flexible input (game ID, team, date range, or "all")
- Avoids re-processing already-analyzed games
- Stores results in SQLite for easy querying
- Scales from one-off analysis to season-wide analytics

### Why It Matters
- **Efficiency**: No manual file management or duplicate processing
- **Scalability**: Can process hundreds of games without overhead
- **Maintainability**: Clear separation of concerns; easy to debug
- **Flexibility**: Supports multiple input types and query patterns

### Preservation
- `get_game_detail.py` stays untouched (the "gold version")
- Orchestrator is a new layer that calls it
- All stat calculations remain unchanged

---

## Next Action

**Please review and provide feedback on**:
1. Do the requirements align with your vision?
2. Any requirements missing or unclear?
3. Answers to the 5 design questions above?
4. Any concerns about the architecture?

Once approved, we'll move to Phase 1 implementation.

---

**Document Version**: 1.0  
**Status**: Ready for Review  
**Author**: Cascade AI Assistant  
**Reviewed By**: [Pending]
