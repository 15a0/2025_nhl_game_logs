# NHL API Reference & Data Structures

**Document Purpose**: Comprehensive guide to NHL API endpoints, response structures, and how they impact game statistics calculations.

**Last Updated**: October 27, 2025  
**Status**: Production (tested with live game data)

---

## Table of Contents

1. [API Endpoints](#api-endpoints)
2. [Response Structures](#response-structures)
3. [Data Field Mappings](#data-field-mappings)
4. [Statistics Calculations](#statistics-calculations)
5. [Common Pitfalls](#common-pitfalls)
6. [Examples](#examples)

---

## API Endpoints

### 1. Season Endpoint
**URL**: `https://api.nhle.com/stats/rest/en/season`

**Purpose**: Fetch current and historical NHL seasons.

**Response Type**: JSON array of season objects

**Key Fields**:
- `id` (integer): Season ID in format YYYYYYYY (e.g., 20252026 for 2025-26 season)
- `isCurrent` (boolean): Whether this is the current active season
- `formattedSeasonId` (string): Human-readable format (e.g., "2025-26")

**Example**:
```json
[
  {
    "id": 20242025,
    "formattedSeasonId": "2024-25",
    "isCurrent": false,
    "startDate": "2024-10-01",
    "endDate": "2025-04-30"
  },
  {
    "id": 20252026,
    "formattedSeasonId": "2025-26",
    "isCurrent": true,
    "startDate": "2025-10-01",
    "endDate": "2026-04-30"
  }
]
```

**Usage**: Extract current season ID for fetching game schedules.

---

### 2. Schedule Endpoint (by Date)
**URL**: `https://api-web.nhle.com/v1/schedule/{YYYY-MM-DD}`

**Purpose**: Fetch all games scheduled for a specific date.

**Response Type**: JSON object with `gameWeek` array

**Key Fields**:
- `gameWeek` (array): Array of week objects, each containing games
- `gameWeek[].date` (string): ISO date (e.g., "2025-10-07")
- `gameWeek[].games` (array): Array of game objects

**Game Object Fields**:
- `id` (integer): Game ID (e.g., 2025020001)
- `gameDate` (string): ISO timestamp (e.g., "2025-10-07T23:00:00Z")
- `gameType` (integer): 1=Preseason, 2=Regular Season, 3=Playoffs
- `gameState` (string): "FUT" (future), "LIVE" (in progress), "OFF" (finished)
- `awayTeam.abbrev` (string): Away team abbreviation (e.g., "CHI")
- `homeTeam.abbrev` (string): Home team abbreviation (e.g., "FLA")

**Example**:
```json
{
  "gameWeek": [
    {
      "date": "2025-10-07",
      "games": [
        {
          "id": 2025020001,
          "gameDate": "2025-10-07T23:00:00Z",
          "gameType": 2,
          "gameState": "OFF",
          "awayTeam": {
            "abbrev": "CHI",
            "id": 16
          },
          "homeTeam": {
            "abbrev": "FLA",
            "id": 13
          }
        }
      ]
    }
  ]
}
```

**Usage**: Build schedule for a season by looping through dates (Oct 1 → May 1).

---

### 3. Boxscore Endpoint
**URL**: `https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/boxscore`

**Purpose**: Fetch team and player-level stats for a completed game.

**Response Type**: JSON object with team stats and player stats

**Key Fields**:
- `gameDate` (string): ISO date
- `homeTeam` (object): Home team stats
- `awayTeam` (object): Away team stats
- `homeTeam.abbrev` (string): Team abbreviation
- `homeTeam.id` (integer): Team ID
- `homeTeam.score` (integer): Final score
- `homeTeam.powerPlayGoals` (integer): PP goals scored
- `homeTeam.powerPlayOpportunities` (integer): PP opportunities
- `homeTeam.powerPlayGoalsAgainst` (integer): PP goals allowed
- `homeTeam.powerPlayOpportunitiesAgainst` (integer): PP opportunities against
- `homeTeam.faceoffWinningPct` (float): Faceoff win percentage (0.0-1.0)

**Example**:
```json
{
  "gameDate": "2025-10-07T23:00:00Z",
  "homeTeam": {
    "abbrev": "FLA",
    "id": 13,
    "score": 4,
    "powerPlayGoals": 0,
    "powerPlayOpportunities": 1,
    "powerPlayGoalsAgainst": 0,
    "powerPlayOpportunitiesAgainst": 2,
    "faceoffWinningPct": 0.52
  },
  "awayTeam": {
    "abbrev": "CHI",
    "id": 16,
    "score": 3,
    "powerPlayGoals": 0,
    "powerPlayOpportunities": 2,
    "powerPlayGoalsAgainst": 0,
    "powerPlayOpportunitiesAgainst": 1,
    "faceoffWinningPct": 0.48
  }
}
```

**Usage**: Extract team-level stats (PP%, PK%, FOW%).

---

### 4. Play-by-Play Endpoint
**URL**: `https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/play-by-play`

**Purpose**: Fetch event-level data (shots, goals, penalties, etc.) for a game.

**Response Type**: JSON object with `plays` array

**Key Fields**:
- `gameState` (string): "FUT", "LIVE", "OFF", "FINAL"
- `plays` (array): Array of play/event objects

**Play Object Structure**:
```json
{
  "eventId": 101,
  "typeCode": 508,
  "typeDescKey": "blocked-shot",
  "periodDescriptor": {
    "number": 1,
    "periodType": "REG"
  },
  "timeInPeriod": "00:22",
  "details": {
    "xCoord": -61,
    "yCoord": 3,
    "zoneCode": "D",
    "eventOwnerTeamId": 13,
    "shootingPlayerId": 8473419,
    "blockingPlayerId": 8482807,
    "shotType": "Wrist",
    "reason": "blocked"
  }
}
```

**Critical Fields**:
- `typeDescKey` (string): Event type (see table below)
- `details.xCoord` (integer): X coordinate on ice (-100 to 100, net at ±89)
- `details.yCoord` (integer): Y coordinate on ice (-42.5 to 42.5)
- `details.eventOwnerTeamId` (integer): Team that made the play
- `details.shotType` (string): Type of shot ("Wrist", "Slap", "Snap", "Backhand")

**Event Type Codes** (`typeDescKey`):
| Event | Code | Notes |
|-------|------|-------|
| `shot-on-goal` | 505 | Counts toward Corsi |
| `missed-shot` | 506 | Counts toward Corsi |
| `blocked-shot` | 508 | Counts toward Corsi |
| `goal` | 503 | Counts toward Corsi & scoring |
| `penalty` | 504 | Penalty event |
| `faceoff` | 402 | Faceoff event |
| `period-start` | 520 | Period start marker |

**Usage**: Extract shot locations, penalties, and compute advanced stats (Corsi, xG, etc.).

---

## Response Structures

### Schedule Response Structure
```
/v1/schedule/{date}
├── gameWeek (array)
│   └── [0] (object)
│       ├── date (string)
│       └── games (array)
│           └── [0] (game object)
│               ├── id
│               ├── gameDate
│               ├── gameType
│               ├── gameState
│               ├── awayTeam
│               │   ├── abbrev
│               │   └── id
│               └── homeTeam
│                   ├── abbrev
│                   └── id
```

### Boxscore Response Structure
```
/gamecenter/{id}/boxscore
├── gameDate
├── homeTeam (object)
│   ├── abbrev
│   ├── id
│   ├── score
│   ├── powerPlayGoals
│   ├── powerPlayOpportunities
│   ├── powerPlayGoalsAgainst
│   ├── powerPlayOpportunitiesAgainst
│   └── faceoffWinningPct
└── awayTeam (same structure)
```

### Play-by-Play Response Structure
```
/gamecenter/{id}/play-by-play
├── gameState
├── plays (array)
│   └── [0] (play object)
│       ├── eventId
│       ├── typeCode
│       ├── typeDescKey
│       ├── periodDescriptor
│       │   ├── number
│       │   └── periodType
│       ├── timeInPeriod
│       └── details (object)
│           ├── xCoord
│           ├── yCoord
│           ├── eventOwnerTeamId
│           ├── shotType
│           └── [other fields]
```

---

## Data Field Mappings

### Critical Mappings (Common Mistakes)

| Concept | Correct Field | Wrong Field | Impact |
|---------|---------------|-------------|--------|
| Event Type | `typeDescKey` | `typeCode` | typeCode is numeric; use string values |
| Shot Coordinates | `details.xCoord`, `details.yCoord` | `x`, `y` | Top-level x/y don't exist; nested in details |
| Team ID (in play) | `details.eventOwnerTeamId` | `teamId` | teamId is null; use eventOwnerTeamId |
| Team Abbreviation | From boxscore `homeTeam.abbrev` | From play-by-play | Play-by-play has no abbrev; match by ID |
| Plays Array | Top-level `plays` | `gameData.plays.allPlays` | Structure differs from Stats API |
| Game State | `gameState` | `status` | Use gameState for FUT/LIVE/OFF/FINAL |

### Event Type String Values

Use these exact strings when filtering plays:
- `"shot-on-goal"` - Shots on goal (counts in Corsi)
- `"missed-shot"` - Missed shots (counts in Corsi)
- `"blocked-shot"` - Blocked shots (counts in Corsi)
- `"goal"` - Goals (counts in Corsi and scoring)
- `"penalty"` - Penalties
- `"faceoff"` - Faceoffs
- `"period-start"` - Period markers
- `"period-end"` - Period end markers

---

## Statistics Calculations

### 1. Corsi (CF%)
**Definition**: Percentage of all shot attempts (shots, missed shots, blocked shots, goals) a team generates.

**Formula**:
```
CF% = (Corsi For) / (Corsi For + Corsi Against) * 100
```

**Corsi For (CF)**: Count of plays where:
- `typeDescKey` in ["shot-on-goal", "missed-shot", "blocked-shot", "goal"]
- `details.eventOwnerTeamId` == team's ID

**Corsi Against (CA)**: Count of plays where:
- Same event types
- `details.eventOwnerTeamId` != team's ID

**Code Example**:
```python
for play in plays:
    event = play.get("typeDescKey", "")
    team_id = play.get("details", {}).get("eventOwnerTeamId")
    
    if event in ["shot-on-goal", "missed-shot", "blocked-shot", "goal"]:
        if team_id == home_team_id:
            cf += 1
        else:
            ca += 1

cf_pct = (cf / (cf + ca or 1)) * 100
```

---

### 2. High-Danger Chances (HDC%)
**Definition**: Percentage of high-danger shot attempts (close to net, high probability scoring area).

**High-Danger Zone**: 
- X coordinate: `abs(abs(x) - 89) < 15` (within 15 feet of net)
- Y coordinate: `abs(y) < 8.5` (within 8.5 feet of center line)

**Formula**:
```
HDC% = (HDC For) / (HDC For + HDC Against) * 100
```

**Code Example**:
```python
for play in plays:
    details = play.get("details", {})
    x = details.get("xCoord", 0)
    y = details.get("yCoord", 0)
    event = play.get("typeDescKey", "")
    
    is_high_danger = abs(abs(x) - 89) < 15 and abs(y) < 8.5
    
    if event in ["shot-on-goal", "missed-shot", "blocked-shot", "goal"]:
        if is_high_danger:
            if team_id == home_team_id:
                hdc_for += 1
            else:
                hdc_against += 1

hdc_pct = (hdc_for / (hdc_for + hdc_against or 1)) * 100
```

---

### 3. Expected Goals (xG)
**Definition**: Sum of goal probabilities based on shot distance and type.

**xG Model** (simplified):
```
Distance = sqrt((abs(x) - 89)^2 + y^2)

if distance < 15:
    xG = 0.20 (if not Slap shot) or 0.15 (if Slap)
elif distance < 30:
    xG = 0.10 (if not Slap shot) or 0.08 (if Slap)
else:
    xG = 0.05 (if not Slap shot) or 0.03 (if Slap)
```

**Formula**:
```
xGF = Sum of xG for all shots by team
xGA = Sum of xG for all shots against team
```

**Code Example**:
```python
def calculate_xg(x, y, shot_type):
    distance = math.sqrt((abs(x) - 89) ** 2 + y ** 2)
    if distance < 15:
        return 0.2 if shot_type != "Slap" else 0.15
    elif distance < 30:
        return 0.1 if shot_type != "Slap" else 0.08
    else:
        return 0.05 if shot_type != "Slap" else 0.03

for play in plays:
    event = play.get("typeDescKey", "")
    if event in ["shot-on-goal", "goal"]:
        details = play.get("details", {})
        x = details.get("xCoord", 0)
        y = details.get("yCoord", 0)
        shot_type = details.get("shotType", "Wrist")
        xg_val = calculate_xg(x, y, shot_type)
        
        if team_id == home_team_id:
            xgf += xg_val
        else:
            xga += xg_val
```

---

### 4. Power Play % (PP%)
**Definition**: Percentage of power play opportunities converted to goals.

**Formula**:
```
PP% = (Power Play Goals) / (Power Play Opportunities) * 100
```

**Source**: Boxscore endpoint
```python
pp_pct = (home_team.get("powerPlayGoals", 0) / 
          max(home_team.get("powerPlayOpportunities", 1), 1)) * 100
```

---

### 5. Penalty Kill % (PK%)
**Definition**: Percentage of opponent power plays where team did NOT allow a goal.

**Formula**:
```
PK% = (PP Opportunities Against - PP Goals Against) / (PP Opportunities Against) * 100
```

**Source**: Boxscore endpoint
```python
pk_pct = ((home_team.get("powerPlayOpportunitiesAgainst", 0) - 
           home_team.get("powerPlayGoalsAgainst", 0)) /
          max(home_team.get("powerPlayOpportunitiesAgainst", 1), 1)) * 100
```

---

### 6. Faceoff Win % (FOW%)
**Definition**: Percentage of faceoffs won by a team.

**Source**: Boxscore endpoint
```python
fow_pct = home_team.get("faceoffWinningPct", 0) * 100
```

---

### 7. Penalty Metrics
**Definition**: Penalties taken and drawn per 60 minutes of play.

**Formula**:
```
Penalties Taken / 60 = Count of penalties taken
Penalties Drawn / 60 = Count of penalties drawn
Net Penalties / 60 = Penalties Taken - Penalties Drawn
```

**Source**: Play-by-play events
```python
for play in plays:
    if play.get("typeDescKey") == "penalty":
        if team_id == home_team_id:
            pen_taken += 1
        else:
            pen_drawn += 1

pen_taken_60 = pen_taken
pen_drawn_60 = pen_drawn
net_pen_60 = pen_taken - pen_drawn
```

---

## Common Pitfalls

### 1. **Using Wrong Field Names**
❌ **Wrong**:
```python
event = play.get("typeCode")  # Returns 505 (numeric)
if event in ["shot-on-goal"]:  # Never matches!
    pass
```

✅ **Correct**:
```python
event = play.get("typeDescKey")  # Returns "shot-on-goal" (string)
if event in ["shot-on-goal"]:  # Matches!
    pass
```

---

### 2. **Accessing Coordinates at Wrong Level**
❌ **Wrong**:
```python
x = play.get("x", 0)  # Returns 0 (field doesn't exist)
y = play.get("y", 0)  # Returns 0
```

✅ **Correct**:
```python
details = play.get("details", {})
x = details.get("xCoord", 0)  # Returns actual coordinate
y = details.get("yCoord", 0)
```

---

### 3. **Fetching Team Data from Wrong Endpoint**
❌ **Wrong**:
```python
# In play-by-play loop:
team_abbrev = play.get("team", {}).get("abbrev")  # Doesn't exist
```

✅ **Correct**:
```python
# Extract from boxscore first:
home_abbrev = boxscore.get("homeTeam", {}).get("abbrev")
away_abbrev = boxscore.get("awayTeam", {}).get("abbrev")

# Match by ID in play-by-play:
team_id = play.get("details", {}).get("eventOwnerTeamId")
if team_id == home_team_id:
    team_abbrev = home_abbrev
```

---

### 4. **Future Games Have Empty Plays**
❌ **Wrong**: Assuming plays array is always populated
```python
plays = play_by_play.get("plays", [])
# If gameState == "FUT", plays is empty!
```

✅ **Correct**: Check game state first
```python
game_state = play_by_play.get("gameState")
if game_state == "FUT":
    print("Game not yet played; no play-by-play data")
    return None
plays = play_by_play.get("plays", [])
```

---

### 5. **Duplicates in Schedule Loop**
❌ **Wrong**: Not deduplicating games
```python
all_games = []
for date in date_range:
    games = fetch_schedule(date)
    all_games.extend(games)  # Same game appears multiple times!
```

✅ **Correct**: Use a set to track seen game IDs
```python
seen_game_ids = set()
all_games = []
for date in date_range:
    games = fetch_schedule(date)
    for game in games:
        game_id = game.get("id")
        if game_id not in seen_game_ids:
            seen_game_ids.add(game_id)
            all_games.append(game)
```

---

## Examples

### Example 1: Fetch Current Season and Build Schedule
```python
import requests
from datetime import datetime, timedelta

# Get current season
season_resp = requests.get("https://api.nhle.com/stats/rest/en/season")
seasons = season_resp.json()
current_season = next((s for s in seasons if s.get("isCurrent")), None)
season_id = current_season["id"]  # e.g., 20252026

# Build date range (Oct 1 - May 1)
year = int(str(season_id)[:4])
start_date = datetime(year, 10, 1)
end_date = datetime(year + 1, 5, 1)

# Fetch all games
all_games = []
seen_ids = set()
current = start_date

while current <= end_date:
    date_str = current.strftime("%Y-%m-%d")
    resp = requests.get(f"https://api-web.nhle.com/v1/schedule/{date_str}")
    data = resp.json()
    
    for week in data.get("gameWeek", []):
        for game in week.get("games", []):
            game_id = game.get("id")
            if game_id not in seen_ids:
                seen_ids.add(game_id)
                all_games.append(game)
    
    current += timedelta(days=1)

print(f"Found {len(all_games)} unique games")
```

---

### Example 2: Extract Advanced Stats from a Game
```python
import requests
import math

GAME_ID = "2025020001"

# Fetch boxscore and play-by-play
boxscore = requests.get(f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/boxscore").json()
pbp = requests.get(f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/play-by-play").json()

# Extract team info
home_team = boxscore.get("homeTeam", {})
away_team = boxscore.get("awayTeam", {})
home_id = home_team.get("id")
away_id = away_team.get("id")
home_abbrev = home_team.get("abbrev")
away_abbrev = away_team.get("abbrev")

# Initialize stats
stats = {
    home_abbrev: {"cf": 0, "ca": 0, "xgf": 0, "xga": 0},
    away_abbrev: {"cf": 0, "ca": 0, "xgf": 0, "xga": 0}
}

# Process plays
plays = pbp.get("plays", [])
for play in plays:
    details = play.get("details", {})
    event = play.get("typeDescKey", "")
    team_id = details.get("eventOwnerTeamId")
    
    # Determine team
    if team_id == home_id:
        team = home_abbrev
        opp_team = away_abbrev
    elif team_id == away_id:
        team = away_abbrev
        opp_team = home_abbrev
    else:
        continue
    
    # Corsi
    if event in ["shot-on-goal", "missed-shot", "blocked-shot", "goal"]:
        stats[team]["cf"] += 1
        stats[opp_team]["ca"] += 1
        
        # xG
        if event in ["shot-on-goal", "goal"]:
            x = details.get("xCoord", 0)
            y = details.get("yCoord", 0)
            distance = math.sqrt((abs(x) - 89) ** 2 + y ** 2)
            shot_type = details.get("shotType", "Wrist")
            
            if distance < 15:
                xg = 0.2 if shot_type != "Slap" else 0.15
            elif distance < 30:
                xg = 0.1 if shot_type != "Slap" else 0.08
            else:
                xg = 0.05 if shot_type != "Slap" else 0.03
            
            stats[team]["xgf"] += xg
            stats[opp_team]["xga"] += xg

# Calculate percentages
for team in stats:
    cf = stats[team]["cf"]
    ca = stats[team]["ca"]
    total = cf + ca or 1
    cf_pct = (cf / total) * 100
    print(f"{team}: {cf_pct:.1f}% Corsi, {stats[team]['xgf']:.2f} xGF")
```

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| All stats are 0 | Plays array is empty | Check `gameState`; only "OFF"/"FINAL"/"LIVE" have plays |
| Stats don't match | Using wrong field names | Use `typeDescKey`, `details.xCoord`, `details.eventOwnerTeamId` |
| Duplicate games | Not deduplicating in schedule loop | Use `set()` to track seen `game_id` values |
| Team mismatch | Comparing abbrev to ID | Extract abbrev from boxscore; match plays by ID |
| xG always 0 | Coordinates are 0 | Check if play has `details` object; some events (faceoffs) have no coords |

---

## References

- **NHL API Base**: `https://api.nhle.com` and `https://api-web.nhle.com`
- **Game State Values**: "FUT" (future), "LIVE" (in progress), "OFF" (finished), "FINAL" (official)
- **Game Type Values**: 1 (Preseason), 2 (Regular Season), 3 (Playoffs)
- **Coordinate System**: X: -100 to 100 (net at ±89), Y: -42.5 to 42.5

---

**Document Version**: 1.0  
**Tested Endpoints**: ✅ Season, ✅ Schedule, ✅ Boxscore, ✅ Play-by-Play  
**Last Verified**: 2025-10-27 with game 2025020001 (FLA vs CHI)
