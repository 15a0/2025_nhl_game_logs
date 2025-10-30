"""Check what the last run produced."""
import sqlite3

db_path = "Data/test_nhl_stats.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check prod
cursor.execute("SELECT COUNT(*) FROM team_game_stats")
prod_count = cursor.fetchone()[0]
print(f"Rows in prod: {prod_count}")

# Check unique games
cursor.execute("SELECT COUNT(DISTINCT game_id) FROM team_game_stats")
unique_games = cursor.fetchone()[0]
print(f"Unique games in prod: {unique_games}")

# Expected: ~275 games × 2 rows = 550 rows
print(f"\nExpected: ~275 games × 2 rows = ~550 rows")
print(f"Actual: {prod_count} rows")
print(f"Missing: {550 - prod_count} rows")

conn.close()
