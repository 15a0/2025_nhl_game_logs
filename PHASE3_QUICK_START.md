# Phase 3: Quick Start & Validation

## Run Phase 3 Validation

```bash
cd c:\Users\jhenk\Documents\GitProjects\NHLGameLogs
python tests/test_phase3_validation.py
```

## What You'll See

### Test 1: DB Schema Creation
- Creates SQLite database with 3 tables
- Creates 3 indexes for fast queries
- Verifies schema structure

**Output**:
```
✓ Tables created: ['games', 'team_game_stats', 'team_aggregates']
✓ Indexes created: [...]
```

### Test 2: DB Insert & Query
- Fetches real game data from NHL API
- Calculates stats using Phase 1 modules
- Inserts game record and team stats (2 rows)
- Queries data back from database

**Output**:
```
✓ Inserted game 2025020001
✓ Inserted team stats (2 rows)
✓ Retrieved 2 rows
  FLA: CF%=58.0, xGF=4.37, xGA=1.46
  CHI: CF%=42.0, xGF=1.46, xGA=4.37
✓ Game exists in database
```

### Test 3: Season Stats Aggregation
- Aggregates all games in date range
- Calculates averages for all 13 stats
- Shows per-team season performance

**Output**:
```
✓ Aggregated stats for 2 teams

FLA Season Stats:
  Games: 1
  CF% Avg: 58.0
  xGF Avg: 4.37
  xGA Avg: 1.46

CHI Season Stats:
  Games: 1
  CF% Avg: 42.0
  xGF Avg: 1.46
  xGA Avg: 4.37
```

### Test 4: Rolling Stats (Last 5 Games)
- Aggregates last N games for each team
- Calculates rolling averages
- Shows form-based performance

**Output**:
```
✓ Aggregated rolling stats for 2 teams

FLA Last 5 Games:
  Games: 1
  CF% Avg: 58.0
  xGF Avg: 4.37
  xGA Avg: 1.46

CHI Last 5 Games:
  Games: 1
  CF% Avg: 42.0
  xGF Avg: 1.46
  xGA Avg: 4.37
```

### Test 5: League Context (for Z-Scores)
- Calculates league-wide mean and std dev
- Provides normalization context for z-scores
- Shows distribution across all teams

**Output**:
```
✓ Calculated context for 13 stats

League Context (Mean ± Std Dev):
  cf_pct: 50.0 ± 8.0 (n=2 teams)
  xgf: 2.92 ± 1.45 (n=2 teams)
  xga: 2.92 ± 1.45 (n=2 teams)
  ...
```

### Test 6: Database Schema Inspection
- Shows table structure (columns and types)
- Shows data counts
- Verifies database integrity

**Output**:
```
Games Table Schema:
  game_id: TEXT
  date: TEXT
  season: INTEGER
  ...

Team Game Stats Table Schema:
  id: INTEGER
  game_id: TEXT
  team: TEXT
  cf_pct: REAL
  ...

Data Counts:
  Games: 1
  Team Game Stats: 2
  Team Aggregates: 0
```

## Database File Location

After running tests, you can inspect the database:

```bash
# View with SQLite CLI
sqlite3 Data/test_nhl_stats.db

# Inside SQLite CLI:
sqlite> SELECT * FROM games;
sqlite> SELECT * FROM team_game_stats;
sqlite> SELECT * FROM team_aggregates;
```

## What the Tests Validate

✅ **DBManager**:
- Schema creation (3 tables, 3 indexes)
- Insert operations (games, team stats)
- Query operations (by game, by team, by date)
- Data integrity (UNIQUE constraints)

✅ **StatsAggregator**:
- Season stats aggregation
- Rolling window aggregation (last N games)
- League context calculation (mean/std)
- Multi-team aggregation

✅ **Integration**:
- Phase 1 (API + Stats) → Phase 3 (DB + Aggregation)
- Real data flow from NHL API to database
- Proper data types and constraints

## Expected Results

All 6 tests should pass with:
- ✅ Database created successfully
- ✅ Data inserted and queried correctly
- ✅ Aggregations calculated accurately
- ✅ League context computed for z-scores
- ✅ Schema verified and intact

## Next Steps After Validation

Once Phase 3 validation passes:

1. **Commit Phase 3** to remote
2. **Build Phase 4**:
   - `zscore_calculator.py` - Z-score normalization
   - `tpi_calculator.py` - TPI calculation
3. **Build Phase 5**:
   - `slate_goi_calculator.py` - Slate GOI calculation

## Troubleshooting

### "Connection failed" Error
- Check internet (Phase 3 fetches real NHL data)
- Verify NHL API is accessible

### "Database locked" Error
- Close any other SQLite connections
- Delete `Data/test_nhl_stats.db` and retry

### "No stats found" Error
- Ensure Phase 1 and Phase 2 are working
- Check that NHL API returns valid data

## Success Criteria

Phase 3 is successful when:
- ✅ All 6 tests pass
- ✅ Database file created at `Data/test_nhl_stats.db`
- ✅ Data inserted and queried correctly
- ✅ Aggregations calculated accurately
- ✅ League context computed for z-scores

---

**Ready to validate Phase 3?**

```bash
python tests/test_phase3_validation.py
```
