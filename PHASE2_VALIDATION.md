# Phase 2: Data Validation

**Status**: Ready to Execute  
**Date**: October 28, 2025  
**Objective**: Validate Phase 1 modules against real NHL API data

## What Phase 2 Does

Phase 2 validates that Phase 1 modules work correctly with real data:

1. ✅ **API Client** - Fetches real boxscore and play-by-play data
2. ✅ **Stats Calculator** - Processes data and calculates 13 stats
3. ✅ **Data Structure** - Validates structure for DB schema design
4. ✅ **Edge Cases** - Handles errors gracefully
5. ✅ **Type Safety** - Confirms data types are correct

## Running Phase 2

### Option 1: Run as Script (Recommended for First Time)

```bash
cd c:\Users\jhenk\Documents\GitProjects\NHLGameLogs
python tests/test_phase2_validation.py
```

**Output**: Detailed logs showing:
- API fetch results
- Stats calculation output
- Data structure breakdown
- Edge case handling
- Pass/Fail status

### Option 2: Run as Pytest

```bash
pytest tests/test_phase2_validation.py -v
```

## What Phase 2 Tests

### Test 1: API Client - Fetch Boxscore
- Fetches real game data (NJD vs COL, Oct 26, 2025)
- Validates boxscore structure
- Confirms team data is present

**Expected Output**:
```
✓ Home Team: NJD (New Jersey Devils)
✓ Away Team: COL (Colorado Avalanche)
✓ Score: 4 - 3
✓ Boxscore keys: [...]
```

### Test 2: API Client - Fetch Play-by-Play
- Fetches real play-by-play data
- Validates play structure
- Confirms event data is present

**Expected Output**:
```
✓ Total plays: 250+
  Play 1: shot-on-goal at (85, 5)
  Play 2: missed-shot at (50, -10)
  ...
```

### Test 3: Stats Calculator - Calculate Game Stats
- Calculates all 13 stats for both teams
- Validates output structure
- Confirms percentages and values are reasonable

**Expected Output**:
```
NJD Stats:
  Tier 1 (Boxscore):
    PP%: 33.3%
    PK%: 75.0%
    FOW%: 52.1%
  Tier 2-4 (Play-by-Play):
    CF%: 52.3%
    SCF%: 48.5%
    HDC%: 55.0%
    xGF: 3.42
    xGA: 2.18
    ...
```

### Test 4: Data Structure Validation
- Inspects boxscore structure
- Inspects play-by-play structure
- Documents field types for DB schema

**Expected Output**:
```
Boxscore Structure:
  Top-level keys: ['homeTeam', 'awayTeam', 'gameDate', ...]
  Home Team keys: ['id', 'abbrev', 'name', 'powerPlayGoals', ...]
    - id: 25 (type: int)
    - abbrev: NJD (type: str)
    - powerPlayGoals: 1 (type: int)

Play-by-Play Structure:
  Top-level keys: ['plays', 'gameState', ...]
  First play keys: ['typeDescKey', 'details', ...]
    - typeDescKey: shot-on-goal (type: str)
    - details keys: ['xCoord', 'yCoord', 'eventOwnerTeamId', ...]
      - xCoord: 85 (type: int)
      - yCoord: 5 (type: int)
      - eventOwnerTeamId: 25 (type: int)
```

### Test 5: Edge Cases
- Tests with None data
- Tests with empty plays
- Validates error handling

**Expected Output**:
```
✓ Handles None boxscore correctly
✓ Handles None play-by-play correctly
✓ Handles empty plays correctly
```

## Phase 2 Output

After running Phase 2, you'll have:

1. **Validation Results** - Confirms all modules work
2. **Data Structure Documentation** - For DB schema design
3. **Sample Stats Output** - Real game data
4. **Error Handling Confirmation** - Edge cases handled

## Next: Phase 3 (DB Schema Design)

Once Phase 2 passes, we'll use the data structure information to design the SQLite schema:

```sql
-- Example (to be refined based on Phase 2 output)
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    date TEXT,
    home_team TEXT,
    away_team TEXT,
    game_state TEXT
);

CREATE TABLE team_game_stats (
    id INTEGER PRIMARY KEY,
    game_id TEXT,
    team TEXT,
    cf_pct REAL,
    scf_pct REAL,
    hdc_pct REAL,
    hdco_pct REAL,
    hdf_pct REAL,
    xgf REAL,
    xga REAL,
    pp_pct REAL,
    pk_pct REAL,
    fow_pct REAL,
    pen_taken_60 INTEGER,
    pen_drawn_60 INTEGER,
    net_pen_60 INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);
```

## Troubleshooting

### "Connection failed" Error
- Check internet connection
- Verify NHL API is accessible: https://api-web.nhle.com/v1/schedule/2025-10-28

### "404 Not Found" Error
- Game ID may not exist
- Try a different game ID from a recent date

### "Import Error" Error
- Ensure you're in the correct directory
- Verify `src/` folder exists
- Run: `python -m pytest` instead of `python tests/...`

## Success Criteria

Phase 2 is successful when:
- ✅ All 5 tests pass
- ✅ API client fetches real data
- ✅ Stats calculator produces valid output
- ✅ Data structure is documented
- ✅ Edge cases are handled

## Ready?

Run Phase 2 now:

```bash
python tests/test_phase2_validation.py
```

Let me know the results!
