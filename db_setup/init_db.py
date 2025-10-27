#!/usr/bin/env python3
"""
Initialize NHL Game Logs SQLite Database

Usage:
    python init_db.py

Creates:
    - Data/nhl_stats.db (SQLite database)
    - games table (schedule reference)
    - game_stats table (advanced statistics)
"""

import sqlite3
import os
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "Data" / "nhl_stats.db"

# SQL schema
SCHEMA = """
-- Games table: Reference data for all games
CREATE TABLE IF NOT EXISTS games (
    game_id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_score INTEGER,
    home_score INTEGER,
    game_state TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Game stats table: Advanced stats (one row per team per game)
CREATE TABLE IF NOT EXISTS game_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    team TEXT NOT NULL,
    opponent TEXT NOT NULL,
    is_home INTEGER NOT NULL,
    cf_pct REAL,
    scf_pct REAL,
    hdc_pct REAL,
    hdco_pct REAL,
    hdf_pct REAL,
    xgf REAL,
    xga REAL,
    pp_pct REAL,
    pk_pct REAL,
    fow_pct REAL,
    pen_taken_60 REAL,
    pen_drawn_60 REAL,
    net_pen_60 REAL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    UNIQUE(game_id, team)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_game_stats_team ON game_stats(team);
CREATE INDEX IF NOT EXISTS idx_game_stats_game_id ON game_stats(game_id);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(date);
CREATE INDEX IF NOT EXISTS idx_games_away_team ON games(away_team);
CREATE INDEX IF NOT EXISTS idx_games_home_team ON games(home_team);
"""

def init_database():
    """Create database and tables"""
    try:
        # Ensure Data directory exists
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database (creates if doesn't exist)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Execute schema
        cursor.executescript(SCHEMA)
        conn.commit()
        
        print(f"✅ Database created successfully: {DB_PATH}")
        
        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"✅ Tables created: {[t[0] for t in tables]}")
        
        # Verify indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = cursor.fetchall()
        print(f"✅ Indexes created: {len(indexes)} total")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    exit(0 if success else 1)
