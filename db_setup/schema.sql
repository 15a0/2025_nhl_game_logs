-- NHL Game Logs Database Schema
-- Created: 2025-10-27
-- Purpose: Store game schedules and advanced statistics

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
    is_home INTEGER NOT NULL,  -- 1 if home team, 0 if away
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
