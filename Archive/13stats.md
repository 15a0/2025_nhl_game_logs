Let's clarify what data is needed for your **13 high-signal stats** and where it comes from, specifically addressing **coordinates** and whether they're available in the **boxscore** or elsewhere. I'll break it down clearly to confirm you have everything you need from the **NHL API** (boxscore and play-by-play endpoints) and highlight which stats require coordinates or additional processing.

---

## Key Points Upfront

- **Boxscore** (/v1/gamecenter/{game_id}/boxscore): Provides **summary stats** (goals, shots, power plays, faceoffs, TOI, etc.) for teams and players. **No coordinates** or event-level details.
- **Play-by-Play** (/v1/gamecenter/{game_id}/play-by-play): Provides **event-level data** (every shot, goal, penalty, etc.) with **coordinates** (xCoord, yCoord), shot types, and game state (e.g., 5v5, power play).
- **Your 13 Stats**:
    - **Direct from Boxscore**: PP%, PK%, FOW%.
    - **Derived from Play-by-Play**: Net Pen/60, Pen Drawn/60, Pen Taken/60, CF%, SCF%, HDC%, HDCO%, HDF%.
    - **Derived with Model**: xGF, xGA (requires play-by-play + an expected goals model).
- **Coordinates**: Only in **play-by-play** for stats like HDC%, HDCO%, HDF%, xGF, xGA. **Not in boxscore**.

You **do need the play-by-play endpoint** for stats involving **shot locations** or **event counts** (penalties, scoring chances). The good news? The NHL API provides all this data, and you’re already set up to fetch it with your game_ids from schedule.csv.

---

## Stat-by-Stat: Data Sources and Coordinates

Here’s a detailed breakdown of your **13 stats**, their **data sources**, whether **coordinates** are needed, and how to get the ingredients.

|**Stat**|**Direct or Derived?**|**Data Source**|**Coordinates Needed?**|**How to Compute**|
|---|---|---|---|---|
|**Net Pen/60**|Derived|Play-by-Play + Boxscore|No|Count penalties taken (eventTypeId: "PENALTY", playerId) and drawn (drewPenalty) from play-by-play. Divide by TOI (from boxscore: playerByGameStats.skaters.toi) × 60.|
|**Pen Drawn/60**|Derived|Play-by-Play + Boxscore|No|Count penalties drawn (drewPenalty) from play-by-play. Divide by TOI (boxscore) × 60.|
|**HDCO%**|Derived|Play-by-Play|Yes|Count high-danger chances on net (shots/goals in slot, using xCoord, yCoord from play-by-play). HDCO / (HDCO + HDCA) × 100.|
|**Pen Taken/60**|Derived|Play-by-Play + Boxscore|No|Count penalties taken (eventTypeId: "PENALTY", playerId) from play-by-play. Divide by TOI (boxscore) × 60.|
|**HDC%**|Derived|Play-by-Play|Yes|Count high-danger chances (shots/goals in slot, using xCoord, yCoord). HDCF / (HDCF + HDCA) × 100.|
|**CF%**|Derived|Play-by-Play|No|Count Corsi events (SHOT, BLOCKED_SHOT, MISSED_SHOT, GOAL) from play-by-play. CF / (CF + CA) × 100.|
|**PP%**|Direct|Boxscore|No|homeTeam.powerPlayGoals / homeTeam.powerPlayOpportunities × 100 (from boxscore).|
|**HDF%**|Derived|Play-by-Play|Yes|Count high-danger shots (SHOT, GOAL in slot, using xCoord, yCoord). HDSF / (HDSF + HDSA) × 100.|
|**FOW%**|Direct|Boxscore|No|homeTeam.faceoffWinningPct or per-player faceoffsWon / (faceoffsWon + faceoffsLost) (from boxscore).|
|**xGF**|Derived|Play-by-Play + xG Model|Yes|Sum expected goals for shots (using xCoord, yCoord, shotType, strength from play-by-play) with an xG model.|
|**SCF%**|Derived|Play-by-Play|Yes (sometimes)|Count scoring chances (SHOT, GOAL with specific criteria, e.g., rebounds or slot shots using xCoord, yCoord). SCF / (SCF + SCA) × 100.|
|**PK%**|Direct|Boxscore|No|(homeTeam.powerPlayOpportunitiesAgainst - homeTeam.powerPlayGoalsAgainst) / powerPlayOpportunitiesAgainst × 100 (from boxscore).|
|**xGA**|Derived|Play-by-Play + xG Model|Yes|Sum expected goals against (using xCoord, yCoord, shotType, strength) with an xG model.|

---

## Coordinates: Where They Come From

- **Source**: **Play-by-Play** endpoint (/v1/gamecenter/{game_id}/play-by-play).
- **JSON Path**: For each event (e.g., plays[i]):
    - xCoord: X-coordinate on rink (-100 to 100, net at ±89).
    - yCoord: Y-coordinate (-42 to 42, center ice at 0).
    - Example: A shot from the slot might be xCoord: 80, yCoord: 5 (right side, near net).
- **Relevant Stats**: Coordinates are critical for:
    - HDCO%, HDC%, HDF%: Identify **high-danger shots/chances** (shots within ~15 ft of net).
    - xGF, xGA: Calculate shot quality based on **distance**, **angle**, and **shot type**.
    - SCF%: Some scoring chances are defined by **location** (e.g., slot shots).

**Boxscore does NOT have coordinates**—it’s aggregated (e.g., total shots, not where they were taken).

---

## Example: Play-by-Play Event with Coordinates

For game_id: 2025020001, a shot event in the play-by-play JSON might look like:

json

```
{
  "eventId": 101,
  "eventTypeId": "SHOT",
  "playerId": 12345,
  "playerName": "Aleksander Barkov",
  "teamId": 13,
  "teamAbbrev": "FLA",
  "xCoord": 80,
  "yCoord": 5,
  "shotType": "Wrist",
  "strength": "EV",
  "period": 1,
  "time": "05:23"
}
```

- **Use Case**:
    - xCoord: 80, yCoord: 5 → High-danger shot (close to net).
    - Feeds into HDC%, HDCO%, HDF%, xGF.