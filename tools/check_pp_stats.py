"""Check PP stats in precalc."""

import sqlite3
import json

db_path = "Data/test_nhl_stats.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Query FLA precalc
cursor.execute("""
    SELECT 
        team, games_count, last_game_id,
        pp_goals_sum, pp_opps_sum,
        pp_goals_against_sum, pp_opps_against_sum,
        cf_sum, xgf_sum
    FROM team_aggregates
    WHERE team = 'FLA' AND window = 'season'
""")

row = cursor.fetchone()

if row:
    print("=" * 70)
    print("FLA PRECALC (team_aggregates)")
    print("=" * 70)
    print(f"Games: {row['games_count']}")
    print(f"Last Game ID: {row['last_game_id']}")
    print(f"\nPower Play:")
    print(f"  PP Goals: {row['pp_goals_sum']}")
    print(f"  PP Opps: {row['pp_opps_sum']}")
    print(f"  PP Goals Against: {row['pp_goals_against_sum']}")
    print(f"  PP Opps Against: {row['pp_opps_against_sum']}")
    print(f"\nOther Stats:")
    print(f"  Corsi For: {row['cf_sum']}")
    print(f"  xGF: {row['xgf_sum']}")
else:
    print("❌ No data found for FLA")

# Also show game-level data for game 1
print("\n" + "=" * 70)
print("GAME-LEVEL DATA (team_game_stats)")
print("=" * 70)

cursor.execute("""
    SELECT 
        game_id, team, side,
        pp_goals, pp_opps,
        pp_goals_against, pp_opps_against,
        cf, xgf
    FROM team_game_stats
    WHERE game_id = '2025020001'
    ORDER BY team
""")

rows = cursor.fetchall()
for row in rows:
    print(f"\n{row['team']} ({row['side']}):")
    print(f"  PP Goals: {row['pp_goals']}, PP Opps: {row['pp_opps']}")
    print(f"  PP GA: {row['pp_goals_against']}, PP Opps Against: {row['pp_opps_against']}")
    print(f"  Corsi For: {row['cf']}, xGF: {row['xgf']}")

conn.close()
