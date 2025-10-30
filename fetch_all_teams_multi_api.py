"""
Production fetcher: Multi-API, async, all 32 teams with staging validation.

Collects game-level data from:
  - Stats API (statsapi.web.nhl.com): PP goals, PP opps, TOI
  - Web API PBP (api-web.nhle.com): Corsi, SCF, HDC, faceoffs, pens, xG

Uses async with 10 concurrent workers, respectful rate limiting, and backoff.
Validates all data before appending to production.

Flow:
  1. Fetch all games into team_game_stats_staging (async, 10 workers)
  2. Validate: row count, nulls, ranges, impossible stats
  3. If PASS: Append to team_game_stats (prod) + clear staging
  4. If FAIL: Clear staging + log errors

Usage:
  python fetch_all_teams_multi_api.py [--clear]
  
  --clear: Clear staging before fetching (default: append to staging)
"""

import sys
import asyncio
import sqlite3
import random
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestrator.assessment import TeamAssessment
from src.orchestrator.fetcher_and_aggregator import GameFetcherAndAggregator

# Constants
MAX_WORKERS = 5  # Reduced from 10 to be more respectful to API
BASE_DELAY = 2.0  # seconds (increased from 1.0)
JITTER_RANGE = (1.0, 2.0)  # random delay per worker (1.0-2.0 sec, increased)
BACKOFF_MULTIPLIER = 2.0
MAX_RETRIES = 2  # Reduced from 3 to avoid hammering API

class AsyncGameFetcher:
    """Async wrapper for game fetching."""
    
    def __init__(self, db_path: str, schedule_path: str):
        self.db_path = db_path
        self.schedule_path = schedule_path
        self.fetcher = GameFetcherAndAggregator(db_path, rate_limit_delay=2.0)
        self.assessor = TeamAssessment(db_path, schedule_path)
        self.schedule = self.assessor.load_schedule()
        self.semaphore = asyncio.Semaphore(MAX_WORKERS)
        self.stats = {
            'teams_processed': 0,
            'games_fetched': 0,
            'games_failed': 0,
            'errors': []
        }
    
    async def fetch_game_with_backoff(self, game_id: str, date: str, home_team: str, away_team: str, retry: int = 0) -> bool:
        """Fetch a single game with exponential backoff."""
        try:
            # Respectful delay with jitter (only on first attempt)
            if retry == 0:
                delay = random.uniform(*JITTER_RANGE)
                await asyncio.sleep(delay)
            
            # Fetch synchronously (API calls are I/O bound, but requests library is sync)
            success = self.fetcher.fetch_and_store_game(game_id, date, home_team, away_team)
            
            if success:
                self.stats['games_fetched'] += 1
            else:
                self.stats['games_failed'] += 1
            
            return success
        
        except Exception as e:
            if retry < MAX_RETRIES:
                backoff = max(0.1, BASE_DELAY * (BACKOFF_MULTIPLIER ** retry))
                print(f"  ⚠️  Retry {retry + 1}/{MAX_RETRIES} for {game_id} (backoff: {backoff:.1f}s)")
                await asyncio.sleep(backoff)
                return await self.fetch_game_with_backoff(game_id, date, home_team, away_team, retry + 1)
            else:
                self.stats['games_failed'] += 1
                self.stats['errors'].append(f"{game_id}: {str(e)}")
                print(f"  ❌ Failed after {MAX_RETRIES} retries: {game_id}")
                return False
    
    def get_already_fetched_games(self, team: str) -> set:
        """Get set of game_ids already fetched for this team (in prod or staging)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check both prod and staging
            cursor.execute(
                "SELECT DISTINCT game_id FROM team_game_stats WHERE team = ?"
                " UNION "
                "SELECT DISTINCT game_id FROM team_game_stats_staging WHERE team = ?",
                (team, team)
            )
            fetched = {row[0] for row in cursor.fetchall()}
            conn.close()
            return fetched
        except Exception as e:
            print(f"  ⚠️  Error checking fetched games: {e}")
            return set()
    
    async def fetch_team_games(self, team: str, game_ids: List[str]) -> int:
        """Fetch unfetched games for a team (async) into staging."""
        schedule_lookup = {g['game_id']: g for g in self.schedule}
        
        # Check which games are already in prod
        already_fetched = self.get_already_fetched_games(team)
        unfetched_game_ids = [gid for gid in game_ids if gid not in already_fetched]
        
        if not unfetched_game_ids:
            print(f"  ✅ All games already fetched for {team}")
            return 0
        
        if len(unfetched_game_ids) < len(game_ids):
            skipped = len(game_ids) - len(unfetched_game_ids)
            print(f"  ⏭️  Skipping {skipped} already-fetched games")
        
        tasks = []
        for i, game_id in enumerate(unfetched_game_ids, 1):
            game_info = schedule_lookup.get(game_id, {})
            date = game_info.get('date', 'N/A')
            home_team = game_info.get('home_team', '?')
            away_team = game_info.get('away_team', '?')
            
            # Create task with semaphore
            async def bounded_fetch():
                async with self.semaphore:
                    return await self.fetch_game_with_backoff(game_id, date, home_team, away_team)
            
            tasks.append(bounded_fetch())
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        return success_count
    
    def validate_staging(self) -> Dict:
        """Validate data in staging table."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        validation = {
            'passed': True,
            'row_count': 0,
            'errors': []
        }
        
        try:
            # Count rows
            cursor.execute("SELECT COUNT(*) as cnt FROM team_game_stats_staging")
            row_count = cursor.fetchone()['cnt']
            validation['row_count'] = row_count
            
            if row_count == 0:
                validation['errors'].append("No rows in staging table")
                validation['passed'] = False
                return validation
            
            # Check for nulls in critical columns
            critical_cols = ['game_id', 'team', 'pp_goals', 'pp_opps', 'cf', 'ca', 'xgf']
            for col in critical_cols:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM team_game_stats_staging WHERE {col} IS NULL")
                null_count = cursor.fetchone()['cnt']
                if null_count > 0:
                    validation['errors'].append(f"{col}: {null_count} NULLs")
                    validation['passed'] = False
            
            # Check for invalid ranges
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM team_game_stats_staging
                WHERE pp_goals < 0 OR pp_opps < 0 OR cf < 0 OR ca < 0 OR xgf < 0
            """)
            invalid_count = cursor.fetchone()['cnt']
            if invalid_count > 0:
                validation['errors'].append(f"Invalid negative values: {invalid_count} rows")
                validation['passed'] = False
            
            # Check for unreasonable PP%
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM team_game_stats_staging
                WHERE pp_opps > 0 AND (pp_goals > pp_opps OR pp_goals_against > pp_opps_against)
            """)
            impossible_count = cursor.fetchone()['cnt']
            if impossible_count > 0:
                validation['errors'].append(f"Impossible PP stats (goals > opps): {impossible_count} rows")
                validation['passed'] = False
            
            # Check for unreasonable CF%
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM team_game_stats_staging
                WHERE (cf + ca) > 0 AND (cf > (cf + ca) * 1.1 OR ca > (cf + ca) * 1.1)
            """)
            cf_anomaly_count = cursor.fetchone()['cnt']
            if cf_anomaly_count > 0:
                validation['errors'].append(f"Anomalous CF/CA ratio: {cf_anomaly_count} rows")
                validation['passed'] = False
        
        except Exception as e:
            validation['errors'].append(f"Validation error: {str(e)}")
            validation['passed'] = False
        
        finally:
            conn.close()
        
        return validation
    
    def pre_fetch_assessment(self, teams_to_fetch: List[tuple]) -> Dict:
        """
        Macro assessment before fetching.
        
        Args:
            teams_to_fetch: List of (team, game_ids) tuples
        
        Returns:
            {
                'total_games_to_fetch': int,
                'games_by_team': Dict[str, int],
                'all_game_ids': Set[str],
                'total_rows_expected': int
            }
        """
        all_game_ids = set()
        games_by_team = {}
        
        for team, game_ids in teams_to_fetch:
            games_by_team[team] = len(game_ids)
            all_game_ids.update(game_ids)
        
        # Each game has 2 rows (home team + away team)
        total_rows_expected = len(all_game_ids) * 2
        
        return {
            'total_games_to_fetch': len(all_game_ids),
            'games_by_team': games_by_team,
            'all_game_ids': all_game_ids,
            'total_rows_expected': total_rows_expected
        }
    
    def post_fetch_validation(self, pre_assessment: Dict) -> bool:
        """
        Validate that we fetched what we expected.
        
        Checks:
        1. Row count matches expected
        2. All expected game_ids are in staging
        3. No unexpected game_ids in staging
        
        Returns:
            True if all checks pass, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM team_game_stats_staging")
            actual_rows = cursor.fetchone()[0]
            expected_rows = pre_assessment['total_rows_expected']
            
            print(f"\n{'='*70}")
            print(f"POST-FETCH VALIDATION")
            print(f"{'='*70}\n")
            
            # Row count check
            print(f"Row count check:")
            print(f"  Expected: {expected_rows}")
            print(f"  Actual:   {actual_rows}")
            if actual_rows != expected_rows:
                print(f"  ❌ MISMATCH")
                return False
            print(f"  ✅ Match")
            
            # Game ID check
            cursor.execute("SELECT DISTINCT game_id FROM team_game_stats_staging")
            actual_game_ids = {row[0] for row in cursor.fetchall()}
            expected_game_ids = pre_assessment['all_game_ids']
            
            print(f"\nGame ID check:")
            print(f"  Expected: {len(expected_game_ids)} unique games")
            print(f"  Actual:   {len(actual_game_ids)} unique games")
            
            missing = expected_game_ids - actual_game_ids
            unexpected = actual_game_ids - expected_game_ids
            
            if missing:
                print(f"  ❌ Missing {len(missing)} game_ids: {sorted(missing)[:5]}...")
                return False
            
            if unexpected:
                print(f"  ❌ Unexpected {len(unexpected)} game_ids: {sorted(unexpected)[:5]}...")
                return False
            
            print(f"  ✅ All game_ids match")
            
            print(f"\n✅ POST-FETCH VALIDATION PASSED\n")
            return True
        
        except Exception as e:
            print(f"❌ Post-fetch validation error: {e}")
            return False
        
        finally:
            conn.close()
    
    def append_staging_to_prod(self) -> bool:
        """Append validated staging data to production table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO team_game_stats 
                (game_id, date, team, side, pp_goals, pp_opps, pp_goals_against, pp_opps_against,
                 faceoff_wins, faceoff_losses, cf, ca, scf, sca, hdc, hdca, hdco, hdcoa, hdsf, hdsfa,
                 xgf, xga, pen_taken, pen_drawn, toi_seconds)
                SELECT game_id, date, team, side, pp_goals, pp_opps, pp_goals_against, pp_opps_against,
                       faceoff_wins, faceoff_losses, cf, ca, scf, sca, hdc, hdca, hdco, hdcoa, hdsf, hdsfa,
                       xgf, xga, pen_taken, pen_drawn, toi_seconds
                FROM team_game_stats_staging
            """)
            conn.commit()
            
            # Clear staging
            cursor.execute("DELETE FROM team_game_stats_staging")
            conn.commit()
            
            print("  ✅ Appended staging to production and cleared staging")
            return True
        
        except sqlite3.Error as e:
            print(f"  ❌ Error appending to production: {e}")
            return False
        
        finally:
            conn.close()
    
    async def fetch_all_teams(self, teams: Optional[List[str]] = None) -> Dict:
        """Fetch all teams concurrently into staging, validate, then append to prod."""
        if teams is None:
            # All 32 NHL teams
            teams = [
                'ANA', 'ARI', 'BOS', 'BUF', 'CAR', 'CBJ', 'CGY', 'CHI',
                'COL', 'DAL', 'DET', 'EDM', 'FLA', 'LAK', 'MIN', 'MTL',
                'NJD', 'NSH', 'NYI', 'NYR', 'OTT', 'PHI', 'PIT', 'SJS',
                'STL', 'TBL', 'TOR', 'VAN', 'VGK', 'WPG', 'WSH', 'SEA'
            ]
        
        print(f"\n{'='*70}")
        print(f"ASSESSING ALL {len(teams)} TEAMS FOR UNFETCHED GAMES")
        print(f"{'='*70}\n")
        
        # First pass: assess all teams and find which have unfetched games
        teams_to_fetch = []
        for team in teams:
            assessment = self.assessor.assess_team(team)
            
            if assessment['unfetched_count'] == 0:
                print(f"  ✅ {team}: All games fetched")
            else:
                print(f"  📥 {team}: {assessment['unfetched_count']} games to fetch")
                teams_to_fetch.append((team, assessment['unfetched_game_ids']))
        
        if not teams_to_fetch:
            print(f"\n✅ All teams up to date. Nothing to fetch.\n")
            return self.stats
        
        # PRE-FETCH ASSESSMENT
        print(f"\n{'='*70}")
        print(f"PRE-FETCH ASSESSMENT")
        print(f"{'='*70}\n")
        pre_assessment = self.pre_fetch_assessment(teams_to_fetch)
        print(f"Total games to fetch: {pre_assessment['total_games_to_fetch']}")
        print(f"Expected rows (2 per game): {pre_assessment['total_rows_expected']}")
        print(f"Games by team: {pre_assessment['games_by_team']}\n")
        
        print(f"\n{'='*70}")
        print(f"FETCHING {len(teams_to_fetch)} TEAMS WITH UNFETCHED GAMES (Async, {MAX_WORKERS} workers)")
        print(f"{'='*70}\n")
        
        # Fetch all teams (writes to staging as it goes)
        for team, unfetched_game_ids in teams_to_fetch:
            print(f"📋 Fetching {team}...")
            
            # Fetch games for this team (async) into staging
            success_count = await self.fetch_team_games(team, unfetched_game_ids)
            
            print(f"  ✅ Fetched {success_count}/{len(unfetched_game_ids)} games for {team}\n")
            self.stats['teams_processed'] += 1
            
            # INLINE VALIDATION: Check row count for this team (fail fast)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM team_game_stats_staging WHERE team = ?", (team,))
            actual_rows_for_team = cursor.fetchone()[0]
            conn.close()
            
            expected_rows_for_team = len(unfetched_game_ids) * 2
            if actual_rows_for_team != expected_rows_for_team:
                print(f"  ⚠️  Row count mismatch for {team}: expected {expected_rows_for_team}, got {actual_rows_for_team}")
                print(f"  ❌ ABORTING - Data integrity issue detected\n")
                self.stats['errors'].append(f"Row count mismatch for {team}: expected {expected_rows_for_team}, got {actual_rows_for_team}")
                return self.stats
        
        # DATA QUALITY VALIDATION
        print(f"\n{'='*70}")
        print(f"DATA QUALITY VALIDATION")
        print(f"{'='*70}\n")
        
        validation = self.validate_staging()
        print(f"Rows in staging: {validation['row_count']}")
        
        if validation['passed']:
            print("✅ All validation checks passed")
            
            # Append to production
            print(f"\n📊 Appending to production...")
            if self.append_staging_to_prod():
                print("✅ Data successfully appended to production\n")
            else:
                print("❌ Failed to append to production\n")
                self.stats['errors'].append("Failed to append staging to production")
        else:
            print("❌ Data quality validation failed:")
            for error in validation['errors']:
                print(f"  - {error}")
            print("\n⚠️  Staging data NOT appended to production (cleared for retry)\n")
            # Clear staging on validation failure
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM team_game_stats_staging")
            conn.commit()
            conn.close()
            self.stats['errors'].append(f"Data quality validation failed: {'; '.join(validation['errors'])}")
        
        return self.stats

def clear_staging():
    """Clear staging table."""
    db_path = "Data/test_nhl_stats.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM team_game_stats_staging")
        conn.commit()
        print("✅ Cleared team_game_stats_staging\n")
    except Exception as e:
        print(f"❌ Error clearing table: {e}\n")
    finally:
        conn.close()

def print_summary(stats: Dict):
    """Print summary statistics."""
    print(f"\n{'='*70}")
    print(f"FETCH SUMMARY")
    print(f"{'='*70}")
    print(f"Teams processed:  {stats['teams_processed']}")
    print(f"Games fetched:    {stats['games_fetched']}")
    print(f"Games failed:     {stats['games_failed']}")
    
    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for error in stats['errors'][:10]:  # Show first 10
            print(f"  - {error}")
        if len(stats['errors']) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more")
    
    print(f"{'='*70}\n")

async def main():
    """Run async fetcher for all teams."""
    clear_flag = '--clear' in sys.argv
    
    if clear_flag:
        clear_staging()
    
    db_path = "Data/test_nhl_stats.db"
    schedule_path = "Data/schedule.csv"
    
    fetcher = AsyncGameFetcher(db_path, schedule_path)
    stats = await fetcher.fetch_all_teams()
    
    print_summary(stats)

if __name__ == "__main__":
    asyncio.run(main())
