"""Reset both staging and prod tables."""
import sqlite3

db_path = "Data/test_nhl_stats.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("DELETE FROM team_game_stats")
    cursor.execute("DELETE FROM team_game_stats_staging")
    conn.commit()
    print("✅ Cleared both team_game_stats and team_game_stats_staging")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    conn.close()
