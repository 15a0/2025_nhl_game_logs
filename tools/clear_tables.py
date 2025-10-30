"""Clear team_game_stats and team_aggregates tables."""

import sqlite3

db_path = "Data/test_nhl_stats.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("DELETE FROM team_game_stats")
cursor.execute("DELETE FROM team_aggregates")
conn.commit()
conn.close()

print("✅ Cleared team_game_stats and team_aggregates")
