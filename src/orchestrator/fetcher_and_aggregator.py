"""
Fetcher and aggregator for the NHL DFS Analytics orchestrator.

Fetches game data from NHL API, stores raw stats, and aggregates to precalc table.
Includes rate limiting to be respectful to NHL.com servers.
"""

import requests
import sqlite3
import time
import random
from pathlib import Path
from typing import Dict, List, Optional

from .raw_extractor import extract_game_raw_stats


class GameFetcherAndAggregator:
    """Fetch games and store raw stats to team_game_stats table."""
    
    def __init__(self, db_path: str, api_timeout: int = 10, rate_limit_delay: float = 2.0):
        """
        Initialize fetcher and aggregator.
        
        Args:
            db_path: Path to SQLite database
            api_timeout: Timeout for API requests (seconds)
            rate_limit_delay: Base delay between fetches (seconds)
        """
        self.db_path = db_path
        self.api_timeout = api_timeout
        self.rate_limit_delay = rate_limit_delay
        self.boxscore_url_template = "https://api-web.nhle.com/v1/gamecenter/{}/boxscore"
        self.pbp_url_template = "https://api-web.nhle.com/v1/gamecenter/{}/play-by-play"
    
    def fetch_boxscore(self, game_id: str) -> Optional[Dict]:
        """
        Fetch boxscore from NHL API.
        
        Args:
            game_id: Game ID (e.g., '2025020001')
        
        Returns:
            Boxscore JSON or None if fetch fails
        """
        try:
            url = self.boxscore_url_template.format(game_id)
            response = requests.get(url, timeout=self.api_timeout)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"  ❌ Boxscore error: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"  ❌ Boxscore fetch failed: {e}")
            return None
    
    def fetch_pbp(self, game_id: str) -> Optional[Dict]:
        """
        Fetch play-by-play from NHL API.
        
        Args:
            game_id: Game ID (e.g., '2025020001')
        
        Returns:
            Play-by-play JSON or None if fetch fails
        """
        try:
            url = self.pbp_url_template.format(game_id)
            response = requests.get(url, timeout=self.api_timeout)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"  PBP error: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"  PBP fetch failed: {e}")
            return None
    
    def insert_game_stats(self, game_id: str, date: str, team: str, side: str, raw_stats: Dict, use_staging: bool = True) -> bool:
        """
        Insert raw game stats into staging or production table.
        
        Uses INSERT OR IGNORE to silently skip duplicates (from retries).
        
        Args:
            game_id: Game ID
            date: Game date
            team: Team abbreviation
            side: 'HOME' or 'AWAY'
            raw_stats: Dict with all raw stats
            use_staging: If True, insert into staging; if False, insert into prod
        
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build column list and values from raw_stats
            columns = ['game_id', 'date', 'team', 'side'] + list(raw_stats.keys())
            values = [game_id, date, team, side] + list(raw_stats.values())
            placeholders = ','.join(['?' for _ in columns])
            
            table_name = 'team_game_stats_staging' if use_staging else 'team_game_stats'
            
            # Use INSERT OR IGNORE to skip duplicates from retries
            insert_sql = f"""
                INSERT OR IGNORE INTO {table_name} ({','.join(columns)})
                VALUES ({placeholders})
            """
            
            cursor.execute(insert_sql, values)
            conn.commit()
            conn.close()
            return True
        
        except sqlite3.Error as e:
            print(f"  ❌ Database error inserting stats: {e}")
            return False
    
    def get_season_totals(self, team: str) -> Optional[Dict]:
        """
        Get season totals for a team by summing all rows in team_game_stats.
        
        This is used for calculating z-scores, TPI, and GOI.
        
        Args:
            team: Team abbreviation
        
        Returns:
            Dict with season totals, or None if error
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as games_count,
                    MAX(game_id) as last_game_id,
                    SUM(pp_goals) as pp_goals,
                    SUM(pp_opps) as pp_opps,
                    SUM(pp_goals_against) as pp_goals_against,
                    SUM(pp_opps_against) as pp_opps_against,
                    SUM(faceoff_wins) as faceoff_wins,
                    SUM(faceoff_losses) as faceoff_losses,
                    SUM(cf) as cf,
                    SUM(ca) as ca,
                    SUM(scf) as scf,
                    SUM(sca) as sca,
                    SUM(hdc) as hdc,
                    SUM(hdca) as hdca,
                    SUM(hdco) as hdco,
                    SUM(hdcoa) as hdcoa,
                    SUM(hdsf) as hdsf,
                    SUM(hdsfa) as hdsfa,
                    SUM(xgf) as xgf,
                    SUM(xga) as xga,
                    SUM(pen_taken) as pen_taken,
                    SUM(pen_drawn) as pen_drawn
                FROM team_game_stats
                WHERE team = ?
            """, (team,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
        
        except sqlite3.Error as e:
            print(f"  ❌ Database error getting season totals: {e}")
            return None
    
    def fetch_and_store_game(self, game_id: str, date: str, home_team: str, away_team: str) -> bool:
        """
        Fetch a single game and store raw stats for both teams.
        
        Includes rate limiting delay.
        
        Args:
            game_id: Game ID
            date: Game date
            home_team: Home team abbreviation
            away_team: Away team abbreviation
        
        Returns:
            True if successful, False otherwise
        """
        # Rate limiting with random jitter (ensure always positive)
        delay = max(0.1, self.rate_limit_delay + random.uniform(-0.5, 0.5))
        print(f"⏳ Waiting {delay:.1f}s before fetching {game_id}...")
        time.sleep(delay)
        
        print(f"📥 Fetching {game_id} ({home_team} vs {away_team})...")
        
        # Fetch data
        boxscore = self.fetch_boxscore(game_id)
        pbp = self.fetch_pbp(game_id)
        
        if not boxscore or not pbp:
            print(f"  ❌ Failed to fetch {game_id}")
            return False
        
        print(f"  ✅ API fetch successful")
        
        # Extract raw stats for both teams
        home_stats = extract_game_raw_stats(boxscore, pbp, game_id, home_team)
        away_stats = extract_game_raw_stats(boxscore, pbp, game_id, away_team)
        
        if not home_stats or not away_stats:
            print(f"  ❌ Failed to extract stats for {game_id}")
            return False
        
        # Store in database
        home_ok = self.insert_game_stats(game_id, date, home_team, 'HOME', home_stats)
        away_ok = self.insert_game_stats(game_id, date, away_team, 'AWAY', away_stats)
        
        if home_ok and away_ok:
            print(f"  ✅ Stored stats for {home_team} and {away_team}")
            return True
        else:
            print(f"  ❌ Failed to store stats for {game_id}")
            return False
    
    def fetch_and_store_team(self, team: str, game_ids: List[str], schedule: List[Dict]) -> bool:
        """
        Fetch all games for a team and store raw stats to team_game_stats.
        
        Season totals are calculated on-demand via get_season_totals().
        
        Args:
            team: Team abbreviation
            game_ids: List of game IDs to fetch
            schedule: List of schedule dicts (for date lookup)
        
        Returns:
            True if all successful, False otherwise
        """
        print(f"\n{'='*70}")
        print(f"FETCHING FOR: {team}")
        print(f"{'='*70}")
        print(f"Games to fetch: {len(game_ids)}\n")
        
        # Create lookup for schedule
        schedule_lookup = {g['game_id']: g for g in schedule}
        
        success_count = 0
        for i, game_id in enumerate(game_ids, 1):
            game_info = schedule_lookup.get(game_id, {})
            date = game_info.get('date', 'N/A')
            home_team = game_info.get('home_team', '?')
            away_team = game_info.get('away_team', '?')
            
            print(f"[{i}/{len(game_ids)}]", end=" ")
            
            if self.fetch_and_store_game(game_id, date, home_team, away_team):
                success_count += 1
            print()
        
        print(f"\n✅ Fetched {success_count}/{len(game_ids)} games")
        
        # Show summary
        totals = self.get_season_totals(team)
        if totals:
            print(f"\n📊 Season totals for {team}:")
            print(f"  Games: {totals['games_count']}")
            print(f"  Corsi For: {totals['cf']}")
            print(f"  xGF: {totals['xgf']}")
        
        return True


# Main entry point
if __name__ == "__main__":
    import sys
    from assessment import TeamAssessment
    
    # Paths
    db_path = Path(__file__).parent.parent.parent / "Data" / "test_nhl_stats.db"
    schedule_path = Path(__file__).parent.parent.parent / "Data" / "schedule.csv"
    
    # Get team from command line
    team = sys.argv[1] if len(sys.argv) > 1 else "FLA"
    
    # Assess
    assessor = TeamAssessment(str(db_path), str(schedule_path))
    assessment = assessor.assess_team(team)
    assessor.print_assessment(assessment)
    
    # Fetch and store
    if assessment['unfetched_count'] > 0:
        fetcher = GameFetcherAndAggregator(str(db_path), rate_limit_delay=2.0)
        schedule = assessor.load_schedule()
        fetcher.fetch_and_store_team(team, assessment['unfetched_game_ids'], schedule)
    else:
        print("✅ All games already fetched!")
