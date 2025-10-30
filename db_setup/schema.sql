-- NHL Game Logs Database Schema
-- Updated: 2025-10-29
-- Purpose: Store game schedules and raw advanced statistics

-- Games table: Reference data for all games
CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    season INTEGER,
    game_type INTEGER,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_team_id INTEGER,
    away_team_id INTEGER,
    game_state TEXT,
    home_score INTEGER,
    away_score INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Team game stats table: Raw stats (one row per team per game)
-- Single source of truth for all per-game statistics
CREATE TABLE IF NOT EXISTS team_game_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    date TEXT NOT NULL,
    team TEXT NOT NULL,
    side TEXT NOT NULL,  -- 'HOME' or 'AWAY'
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
);

-- Team game stats staging table: Temporary staging for validation
-- Used during nightly fetches to validate data before appending to prod
-- Cleared after each successful validation and append
-- Has UNIQUE constraint to prevent duplicate inserts during retries
CREATE TABLE IF NOT EXISTS team_game_stats_staging (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    date TEXT NOT NULL,
    team TEXT NOT NULL,
    side TEXT NOT NULL,  -- 'HOME' or 'AWAY'
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
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_team_game_stats_team ON team_game_stats(team);
CREATE INDEX IF NOT EXISTS idx_team_game_stats_game_id ON team_game_stats(game_id);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(date);
CREATE INDEX IF NOT EXISTS idx_games_away_team ON games(away_team);
CREATE INDEX IF NOT EXISTS idx_games_home_team ON games(home_team);
