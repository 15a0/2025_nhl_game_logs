"""Check staging vs prod state."""
import sqlite3

db_path = "Data/test_nhl_stats.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check staging
cursor.execute("SELECT COUNT(*) FROM team_game_stats_staging")
staging_count = cursor.fetchone()[0]
print(f"Rows in staging: {staging_count}")

# Check prod
cursor.execute("SELECT COUNT(*) FROM team_game_stats")
prod_count = cursor.fetchone()[0]
print(f"Rows in prod: {prod_count}")

# Check prod by team
print("\nProd by team:")
cursor.execute("SELECT team, COUNT(*) as cnt FROM team_game_stats GROUP BY team ORDER BY team")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check staging by team
print("\nStaging by team:")
cursor.execute("SELECT team, COUNT(*) as cnt FROM team_game_stats_staging GROUP BY team ORDER BY team")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
