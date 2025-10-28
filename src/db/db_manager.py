"""
Database Manager for NHL DFS Analytics

Handles SQLite database operations:
- Schema creation (games, team_game_stats, team_aggregates)
- Game stats insertion
- Query operations
- Connection management

Schema Design (from Phase 2 data validation):
- games: Master game records
- team_game_stats: Per-game stats for each team (13 high-signal stats)
- team_aggregates: Aggregated stats (season + rolling windows)

Two-row-per-game pattern:
- Each game has 2 rows in team_game_stats (one per team)
- Enables efficient querying by team or game
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DBManager:
    """
    SQLite database manager for NHL DFS Analytics.
    
    Usage:
        db = DBManager("Data/nhl_stats.db")
        db.init_db()
        db.insert_game_stats(game_id, team_stats)
        stats = db.query_team_stats("FLA", "2025-10-01", "2025-10-31")
    """
    
    def __init__(self, db_path: str = "Data/nhl_stats.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Database path: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Return rows as dicts
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_db(self) -> None:
        """Initialize database schema."""
        logger.info("Initializing database schema...")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Games table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    game_id TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    game_type INTEGER NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    home_team_id INTEGER,
                    away_team_id INTEGER,
                    game_state TEXT,
                    home_score INTEGER,
                    away_score INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Team Game Stats table (two rows per game: one per team)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS team_game_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    team TEXT NOT NULL,
                    team_id INTEGER,
                    side TEXT,
                    
                    -- Tier 1 (Boxscore)
                    pp_pct REAL,
                    pk_pct REAL,
                    fow_pct REAL,
                    
                    -- Tier 2-4 (Play-by-Play)
                    cf_pct REAL,
                    scf_pct REAL,
                    hdc_pct REAL,
                    hdco_pct REAL,
                    hdf_pct REAL,
                    xgf REAL,
                    xga REAL,
                    pen_taken_60 INTEGER,
                    pen_drawn_60 INTEGER,
                    net_pen_60 INTEGER,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(game_id),
                    UNIQUE(game_id, team)
                )
            """)
            
            # Team Aggregates table (season + rolling windows)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS team_aggregates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team TEXT NOT NULL,
                    team_id INTEGER,
                    date TEXT NOT NULL,
                    window TEXT NOT NULL,
                    games_count INTEGER,
                    
                    -- Aggregated stats (averages)
                    pp_pct_avg REAL,
                    pk_pct_avg REAL,
                    fow_pct_avg REAL,
                    cf_pct_avg REAL,
                    scf_pct_avg REAL,
                    hdc_pct_avg REAL,
                    hdco_pct_avg REAL,
                    hdf_pct_avg REAL,
                    xgf_avg REAL,
                    xga_avg REAL,
                    pen_taken_60_avg REAL,
                    pen_drawn_60_avg REAL,
                    net_pen_60_avg REAL,
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(team, date, window)
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON games(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team, away_team)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_game_stats_game ON team_game_stats(game_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_game_stats_team_date ON team_game_stats(team, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_aggregates_team_date ON team_aggregates(team, date)")
            
            logger.info("✓ Database schema initialized")
    
    def insert_game(self, game_data: Dict[str, Any]) -> None:
        """
        Insert game record.
        
        Args:
            game_data: Dict with game_id, date, season, game_type, home_team, away_team, etc.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO games (
                    game_id, date, season, game_type, home_team, away_team,
                    home_team_id, away_team_id, game_state, home_score, away_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_data.get("game_id"),
                game_data.get("date"),
                game_data.get("season"),
                game_data.get("game_type"),
                game_data.get("home_team"),
                game_data.get("away_team"),
                game_data.get("home_team_id"),
                game_data.get("away_team_id"),
                game_data.get("game_state"),
                game_data.get("home_score"),
                game_data.get("away_score")
            ))
            
            logger.debug(f"Inserted game {game_data.get('game_id')}")
    
    def insert_team_game_stats(self, game_id: str, team_stats: Dict[str, Any]) -> None:
        """
        Insert team stats for a game (two rows per game: one per team).
        
        Args:
            game_id: Game ID
            team_stats: Dict with team abbreviation as key, stats dict as value
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for team_abbrev, stats in team_stats.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO team_game_stats (
                        game_id, date, team, team_id, side,
                        pp_pct, pk_pct, fow_pct,
                        cf_pct, scf_pct, hdc_pct, hdco_pct, hdf_pct,
                        xgf, xga, pen_taken_60, pen_drawn_60, net_pen_60
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    game_id,
                    stats.get("date"),
                    team_abbrev,
                    stats.get("team_id"),
                    stats.get("side"),
                    stats.get("pp_pct"),
                    stats.get("pk_pct"),
                    stats.get("fow_pct"),
                    stats.get("cf_pct"),
                    stats.get("scf_pct"),
                    stats.get("hdc_pct"),
                    stats.get("hdco_pct"),
                    stats.get("hdf_pct"),
                    stats.get("xgf"),
                    stats.get("xga"),
                    stats.get("pen_taken_60"),
                    stats.get("pen_drawn_60"),
                    stats.get("net_pen_60")
                ))
            
            logger.debug(f"Inserted team stats for game {game_id}")
    
    def query_team_stats(
        self,
        team: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query team stats for a date range.
        
        Args:
            team: Team abbreviation (e.g., "FLA")
            start_date: Start date (YYYY-MM-DD), optional
            end_date: End date (YYYY-MM-DD), optional
            limit: Max results
        
        Returns:
            List of stat rows
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM team_game_stats WHERE team = ?"
            params = [team]
            
            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            
            query += " ORDER BY date DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def query_game_stats(self, game_id: str) -> List[Dict[str, Any]]:
        """
        Query stats for a specific game (returns 2 rows: one per team).
        
        Args:
            game_id: Game ID
        
        Returns:
            List of 2 stat rows (home and away team)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM team_game_stats WHERE game_id = ? ORDER BY side",
                (game_id,)
            )
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def game_exists(self, game_id: str) -> bool:
        """Check if game has been processed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM team_game_stats WHERE game_id = ? LIMIT 1", (game_id,))
            return cursor.fetchone() is not None
    
    def get_latest_game_date(self) -> Optional[str]:
        """Get the most recent game date in database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM team_game_stats")
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
    
    def get_team_list(self) -> List[str]:
        """Get list of all teams in database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT team FROM team_game_stats ORDER BY team")
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    
    def close(self) -> None:
        """Close database connection (if needed)."""
        pass  # SQLite connections are closed in context manager
