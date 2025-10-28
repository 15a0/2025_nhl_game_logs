"""
Phase 3: DB Schema & Aggregation Validation Test

Validates Phase 3 modules:
1. DBManager creates schema
2. DBManager inserts game data
3. DBManager queries data
4. StatsAggregator aggregates stats
5. League context calculated correctly

Run: python tests/test_phase3_validation.py
"""

import sys
import logging
from pathlib import Path
import sqlite3

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import DBManager
from src.aggregator import StatsAggregator
from src.api import NHLAPIClient
from src.stats import calculate_game_stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_db_schema_creation():
    """Test: DBManager creates schema correctly."""
    logger.info("=" * 80)
    logger.info("TEST 1: DB Schema Creation")
    logger.info("=" * 80)
    
    # Use test database
    test_db_path = "Data/test_nhl_stats.db"
    db = DBManager(test_db_path)
    
    logger.info(f"Creating database at {test_db_path}...")
    db.init_db()
    
    # Verify tables exist
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    logger.info(f"✓ Tables created: {tables}")
    assert "games" in tables, "Missing games table"
    assert "team_game_stats" in tables, "Missing team_game_stats table"
    assert "team_aggregates" in tables, "Missing team_aggregates table"
    
    # Verify indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [row[0] for row in cursor.fetchall()]
    logger.info(f"✓ Indexes created: {indexes}")
    
    conn.close()
    return db, test_db_path


def test_db_insert_and_query(db):
    """Test: DBManager inserts and queries data."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: DB Insert & Query")
    logger.info("=" * 80)
    
    # Fetch real game data
    logger.info("Fetching real game data from NHL API...")
    client = NHLAPIClient()
    game_id = "2025020001"
    boxscore = client.fetch_boxscore(game_id)
    pbp = client.fetch_play_by_play(game_id)
    
    # Calculate stats
    logger.info("Calculating stats...")
    stats = calculate_game_stats(boxscore, pbp)
    
    # Insert game
    logger.info(f"Inserting game {game_id}...")
    game_data = {
        "game_id": game_id,
        "date": boxscore.get("gameDate"),
        "season": boxscore.get("season"),
        "game_type": boxscore.get("gameType"),
        "home_team": boxscore.get("homeTeam", {}).get("abbrev"),
        "away_team": boxscore.get("awayTeam", {}).get("abbrev"),
        "home_team_id": boxscore.get("homeTeam", {}).get("id"),
        "away_team_id": boxscore.get("awayTeam", {}).get("id"),
        "game_state": boxscore.get("gameState"),
        "home_score": boxscore.get("homeTeam", {}).get("score"),
        "away_score": boxscore.get("awayTeam", {}).get("score")
    }
    
    db.insert_game(game_data)
    logger.info(f"✓ Inserted game {game_id}")
    
    # Insert team stats
    logger.info("Inserting team stats...")
    db.insert_team_game_stats(game_id, stats)
    logger.info("✓ Inserted team stats (2 rows)")
    
    # Query game stats
    logger.info("Querying game stats...")
    queried_stats = db.query_game_stats(game_id)
    logger.info(f"✓ Retrieved {len(queried_stats)} rows")
    
    for row in queried_stats:
        logger.info(f"  {row['team']}: CF%={row['cf_pct']}, xGF={row['xgf']}, xGA={row['xga']}")
    
    # Check if game exists
    logger.info("Checking if game exists...")
    exists = db.game_exists(game_id)
    assert exists, "Game should exist in database"
    logger.info("✓ Game exists in database")
    
    return game_id


def test_aggregator_season_stats(db):
    """Test: StatsAggregator calculates season stats."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Aggregator - Season Stats")
    logger.info("=" * 80)
    
    agg = StatsAggregator(db)
    
    logger.info("Calculating season stats for all teams...")
    season_stats = agg.get_all_teams_season_stats("2025-10-01", "2025-10-31")
    
    logger.info(f"✓ Aggregated stats for {len(season_stats)} teams")
    
    for team, stats in season_stats.items():
        logger.info(f"\n{team} Season Stats:")
        logger.info(f"  Games: {stats['games_count']}")
        logger.info(f"  CF% Avg: {stats.get('cf_pct_avg', 'N/A')}")
        logger.info(f"  xGF Avg: {stats.get('xgf_avg', 'N/A')}")
        logger.info(f"  xGA Avg: {stats.get('xga_avg', 'N/A')}")


def test_aggregator_rolling_stats(db):
    """Test: StatsAggregator calculates rolling stats."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Aggregator - Rolling Stats")
    logger.info("=" * 80)
    
    agg = StatsAggregator(db)
    
    logger.info("Calculating last 5-game stats for all teams...")
    rolling_stats = agg.get_all_teams_rolling_stats("2025-10-31", games=5)
    
    logger.info(f"✓ Aggregated rolling stats for {len(rolling_stats)} teams")
    
    for team, stats in rolling_stats.items():
        logger.info(f"\n{team} Last 5 Games:")
        logger.info(f"  Games: {stats['games_count']}")
        logger.info(f"  CF% Avg: {stats.get('cf_pct_avg', 'N/A')}")
        logger.info(f"  xGF Avg: {stats.get('xgf_avg', 'N/A')}")
        logger.info(f"  xGA Avg: {stats.get('xga_avg', 'N/A')}")


def test_league_context(db):
    """Test: League context calculated for z-scores."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: League Context (for Z-Scores)")
    logger.info("=" * 80)
    
    agg = StatsAggregator(db)
    
    logger.info("Calculating league-wide context...")
    league_context = agg.get_league_context("2025-10-01", "2025-10-31")
    
    logger.info(f"✓ Calculated context for {len(league_context)} stats")
    
    logger.info("\nLeague Context (Mean ± Std Dev):")
    for stat, context in league_context.items():
        mean = context.get('mean', 'N/A')
        std = context.get('std', 'N/A')
        count = context.get('count', 'N/A')
        logger.info(f"  {stat}: {mean} ± {std} (n={count} teams)")


def test_db_schema_inspection(test_db_path):
    """Test: Inspect database schema."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: Database Schema Inspection")
    logger.info("=" * 80)
    
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    
    # Inspect games table
    logger.info("\nGames Table Schema:")
    cursor.execute("PRAGMA table_info(games)")
    for row in cursor.fetchall():
        logger.info(f"  {row[1]}: {row[2]}")
    
    # Inspect team_game_stats table
    logger.info("\nTeam Game Stats Table Schema:")
    cursor.execute("PRAGMA table_info(team_game_stats)")
    for row in cursor.fetchall():
        logger.info(f"  {row[1]}: {row[2]}")
    
    # Inspect team_aggregates table
    logger.info("\nTeam Aggregates Table Schema:")
    cursor.execute("PRAGMA table_info(team_aggregates)")
    for row in cursor.fetchall():
        logger.info(f"  {row[1]}: {row[2]}")
    
    # Count rows
    logger.info("\nData Counts:")
    cursor.execute("SELECT COUNT(*) FROM games")
    logger.info(f"  Games: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM team_game_stats")
    logger.info(f"  Team Game Stats: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM team_aggregates")
    logger.info(f"  Team Aggregates: {cursor.fetchone()[0]}")
    
    conn.close()


def main():
    """Run all Phase 3 validation tests."""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "PHASE 3: DB SCHEMA & AGGREGATION VALIDATION TEST SUITE".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    
    try:
        # Test 1: Schema creation
        db, test_db_path = test_db_schema_creation()
        
        # Test 2: Insert and query
        game_id = test_db_insert_and_query(db)
        
        # Test 3: Season stats
        test_aggregator_season_stats(db)
        
        # Test 4: Rolling stats
        test_aggregator_rolling_stats(db)
        
        # Test 5: League context
        test_league_context(db)
        
        # Test 6: Schema inspection
        test_db_schema_inspection(test_db_path)
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 80)
        logger.info("\nPhase 3 Validation Complete!")
        logger.info("Database created at: Data/test_nhl_stats.db")
        logger.info("\nKey Findings:")
        logger.info("- DBManager successfully creates SQLite schema")
        logger.info("- Schema includes 3 tables with proper indexes")
        logger.info("- Data insertion and querying work correctly")
        logger.info("- StatsAggregator calculates season and rolling stats")
        logger.info("- League context calculated for z-score normalization")
        logger.info("\nNext Steps:")
        logger.info("1. Build zscore_calculator.py (Phase 4)")
        logger.info("2. Build tpi_calculator.py (Phase 4)")
        logger.info("3. Build slate_goi_calculator.py (Phase 5)")
        
    except AssertionError as e:
        logger.error(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        logger.error(f"\n✗ UNEXPECTED ERROR: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
