"""Recreate staging table with UNIQUE constraint."""
import sqlite3

db_path = "Data/test_nhl_stats.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Drop old staging table
    cursor.execute("DROP TABLE IF EXISTS team_game_stats_staging")
    
    # Create new staging table with UNIQUE constraint
    cursor.execute("""
        CREATE TABLE team_game_stats_staging (
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(game_id, team)
        )
    """)
    
    conn.commit()
    print("✅ Recreated team_game_stats_staging with UNIQUE constraint")
    
except Exception as e:
    print(f"❌ Error: {e}")
    
finally:
    conn.close()
