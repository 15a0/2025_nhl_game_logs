"""Debug database state."""
import sqlite3

db_path = "Data/test_nhl_stats.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:")
for table in tables:
    print(f"  - {table[0]}")

# Check row counts
print("\nRow counts:")
for table in ['team_game_stats', 'team_game_stats_staging']:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")
    except Exception as e:
        print(f"  {table}: ERROR - {e}")

# Check a sample from prod
print("\nSample from team_game_stats (first 3 rows):")
try:
    cursor.execute("SELECT game_id, team FROM team_game_stats LIMIT 3")
    for row in cursor.fetchall():
        print(f"  {row}")
except Exception as e:
    print(f"  ERROR: {e}")

conn.close()
