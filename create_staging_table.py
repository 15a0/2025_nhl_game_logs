"""Create staging table in database."""
import sqlite3

db_path = "Data/test_nhl_stats.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_game_stats_staging (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            date TEXT NOT NULL,
            team TEXT NOT NULL,
            side TEXT NOT NULL,
            pp_goals INTEGER,
            pp_opps INTEGER,
            pp_goals_against INTEGER,
            pp_opps_against INTEGER,
            faceoff_wins INTEGER,
            faceoff_losses INTEGER,
            cf INTEGER,
            ca INTEGER,
            scf INTEGER,
            sca INTEGER,
            hdc INTEGER,
            hdca INTEGER,
            hdco INTEGER,
            hdcoa INTEGER,
            hdsf INTEGER,
            hdsfa INTEGER,
            xgf REAL,
            xga REAL,
            pen_taken INTEGER,
            pen_drawn INTEGER,
            toi_seconds INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print("✅ Created team_game_stats_staging table")
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    conn.close()
