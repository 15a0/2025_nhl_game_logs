"""
Assessment module for the NHL DFS Analytics orchestrator.

Evaluates what data has been fetched and what remains to be fetched for a given team.
"""

import csv
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


class TeamAssessment:
    """Assess data completeness for a team."""
    
    def __init__(self, db_path: str, schedule_path: str):
        """
        Initialize assessment module.
        
        Args:
            db_path: Path to SQLite database
            schedule_path: Path to schedule.csv
        """
        self.db_path = db_path
        self.schedule_path = schedule_path
    
    def load_schedule(self) -> List[Dict]:
        """
        Load schedule from CSV.
        
        Returns:
            List of game dicts with keys: game_id, date, home_team, away_team, game_state
        """
        schedule = []
        try:
            with open(self.schedule_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='|')
                for row in reader:
                    schedule.append(row)
            return schedule
        except FileNotFoundError:
            print(f"Schedule file not found: {self.schedule_path}")
            return []
    
    def get_precalc_row(self, team: str) -> Optional[Dict]:
        """
        Query team_game_stats for team's last processed game.
        
        Args:
            team: Team abbreviation (e.g., 'FLA')
        
        Returns:
            Dict with last_game_id, games_count, or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT 
                    MAX(game_id) as last_game_id,
                    COUNT(*) as games_count
                FROM team_game_stats 
                WHERE team = ?
                """,
                (team,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row['games_count'] > 0:
                return {
                    'last_game_id': row['last_game_id'],
                    'games_count': row['games_count']
                }
            return None
        
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None
    
    def assess_team(self, team: str) -> Dict:
        """
        Assess data completeness for a team.
        
        Args:
            team: Team abbreviation (e.g., 'FLA')
        
        Returns:
            Dict with assessment results:
            {
                'team': str,
                'last_game_id': str or None,
                'games_count': int,
                'total_completed': int,
                'unfetched_count': int,
                'unfetched_game_ids': List[str]
            }
        """
        # Get precalc row
        precalc = self.get_precalc_row(team)
        
        # Load schedule
        schedule = self.load_schedule()
        
        # Filter for this team's completed games
        team_games = [
            g for g in schedule
            if (g.get('home_team') == team or g.get('away_team') == team)
            and g.get('game_state') == 'OFF'
        ]
        
        # Get games already in database (prod + staging)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT game_id FROM team_game_stats WHERE team = ?"
                " UNION "
                "SELECT DISTINCT game_id FROM team_game_stats_staging WHERE team = ?",
                (team, team)
            )
            fetched_game_ids = {row[0] for row in cursor.fetchall()}
            conn.close()
            # Debug: show what we found
            if fetched_game_ids:
                print(f"  Found {len(fetched_game_ids)} games already in database")
        except Exception as e:
            print(f"  ⚠️  Error checking database: {e}")
            fetched_game_ids = set()
        
        # Find unfetched games (in schedule but not in database)
        unfetched = [
            g for g in team_games
            if g['game_id'] not in fetched_game_ids
        ]
        
        return {
            'team': team,
            'last_game_id': precalc['last_game_id'] if precalc else None,
            'games_count': precalc['games_count'] if precalc else 0,
            'total_completed': len(team_games),
            'unfetched_count': len(unfetched),
            'unfetched_game_ids': [g['game_id'] for g in unfetched]
        }
    
    def print_assessment(self, assessment: Dict) -> None:
        """
        Pretty-print assessment results.
        
        Args:
            assessment: Assessment dict from assess_team()
        """
        print(f"\n{'='*70}")
        print(f"ASSESSMENT: {assessment['team']}")
        print(f"{'='*70}")
        print(f"Last game fetched:     {assessment['last_game_id'] or 'None (precalc empty)'}")
        print(f"Games in precalc:      {assessment['games_count']}")
        print(f"Total completed games: {assessment['total_completed']}")
        print(f"Unfetched games:       {assessment['unfetched_count']}")
        
        if assessment['unfetched_game_ids']:
            print(f"\nGame IDs to fetch:")
            for game_id in assessment['unfetched_game_ids']:
                print(f"  - {game_id}")
        else:
            print(f"\n✅ All completed games have been fetched!")
        print(f"{'='*70}\n")


# Main entry point
if __name__ == "__main__":
    import sys
    
    # Paths
    db_path = Path(__file__).parent.parent.parent / "Data" / "test_nhl_stats.db"
    schedule_path = Path(__file__).parent.parent.parent / "Data" / "schedule.csv"
    
    # Create assessment module
    assessor = TeamAssessment(str(db_path), str(schedule_path))
    
    # Get team from command line or use default
    team = sys.argv[1] if len(sys.argv) > 1 else "FLA"
    
    # Run assessment
    result = assessor.assess_team(team)
    assessor.print_assessment(result)
