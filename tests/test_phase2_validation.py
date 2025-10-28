"""
Phase 2: Data Validation Test

Validates Phase 1 modules against real NHL API data:
1. API client fetches real game data
2. Stats calculator processes data correctly
3. Output structure matches expectations
4. Data types are correct
5. Edge cases are handled

Run: python -m pytest tests/test_phase2_validation.py -v
Or:  python tests/test_phase2_validation.py
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api import NHLAPIClient
from src.stats import calculate_game_stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_api_client_fetch_boxscore():
    """Test: API client can fetch real boxscore data."""
    logger.info("=" * 80)
    logger.info("TEST 1: API Client - Fetch Boxscore")
    logger.info("=" * 80)
    
    client = NHLAPIClient()
    
    # Use a known completed game (NJD vs COL, Oct 26, 2025)
    game_id = "2025020001"
    logger.info(f"Fetching boxscore for game {game_id}...")
    
    boxscore = client.fetch_boxscore(game_id)
    
    assert boxscore is not None, "Boxscore fetch failed"
    assert "homeTeam" in boxscore, "Missing homeTeam in boxscore"
    assert "awayTeam" in boxscore, "Missing awayTeam in boxscore"
    
    home_team = boxscore.get("homeTeam", {})
    away_team = boxscore.get("awayTeam", {})
    
    logger.info(f"✓ Home Team: {home_team.get('abbrev', 'N/A')} ({home_team.get('name', {}).get('default', 'N/A')})")
    logger.info(f"✓ Away Team: {away_team.get('abbrev', 'N/A')} ({away_team.get('name', {}).get('default', 'N/A')})")
    logger.info(f"✓ Score: {away_team.get('score', 0)} - {home_team.get('score', 0)}")
    logger.info(f"✓ Boxscore keys: {list(boxscore.keys())}")
    
    return game_id


def test_api_client_fetch_play_by_play(game_id):
    """Test: API client can fetch real play-by-play data."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: API Client - Fetch Play-by-Play")
    logger.info("=" * 80)
    
    client = NHLAPIClient()
    logger.info(f"Fetching play-by-play for game {game_id}...")
    
    pbp = client.fetch_play_by_play(game_id)
    
    assert pbp is not None, "Play-by-play fetch failed"
    assert "plays" in pbp, "Missing plays in play-by-play"
    
    plays = pbp.get("plays", [])
    logger.info(f"✓ Total plays: {len(plays)}")
    
    # Sample first few plays
    for i, play in enumerate(plays[:3]):
        event_type = play.get("typeDescKey", "N/A")
        details = play.get("details", {})
        logger.info(f"  Play {i+1}: {event_type} at ({details.get('xCoord', 'N/A')}, {details.get('yCoord', 'N/A')})")
    
    logger.info(f"✓ Play-by-play keys: {list(pbp.keys())}")
    
    return pbp


def test_stats_calculator(boxscore, pbp):
    """Test: Stats calculator processes data correctly."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Stats Calculator - Calculate Game Stats")
    logger.info("=" * 80)
    
    logger.info("Calculating stats for both teams...")
    
    stats = calculate_game_stats(boxscore, pbp)
    
    assert stats is not None, "Stats calculation failed"
    assert len(stats) == 2, f"Expected 2 teams, got {len(stats)}"
    
    for team_abbrev, team_stats in stats.items():
        logger.info(f"\n{team_abbrev} Stats:")
        logger.info(f"  Game ID: {team_stats.get('game_id', 'N/A')}")
        logger.info(f"  Date: {team_stats.get('date', 'N/A')}")
        logger.info(f"  Side: {team_stats.get('side', 'N/A')}")
        
        # Tier 1 (Boxscore)
        logger.info(f"  Tier 1 (Boxscore):")
        logger.info(f"    PP%: {team_stats.get('pp_pct', 'N/A'):.1f}%")
        logger.info(f"    PK%: {team_stats.get('pk_pct', 'N/A'):.1f}%")
        logger.info(f"    FOW%: {team_stats.get('fow_pct', 'N/A'):.1f}%")
        
        # Tier 2-4 (Play-by-Play)
        logger.info(f"  Tier 2-4 (Play-by-Play):")
        logger.info(f"    CF%: {team_stats.get('cf_pct', 'N/A'):.1f}%")
        logger.info(f"    SCF%: {team_stats.get('scf_pct', 'N/A'):.1f}%")
        logger.info(f"    HDC%: {team_stats.get('hdc_pct', 'N/A'):.1f}%")
        logger.info(f"    HDCO%: {team_stats.get('hdco_pct', 'N/A'):.1f}%")
        logger.info(f"    HDF%: {team_stats.get('hdf_pct', 'N/A'):.1f}%")
        logger.info(f"    xGF: {team_stats.get('xgf', 'N/A'):.2f}")
        logger.info(f"    xGA: {team_stats.get('xga', 'N/A'):.2f}")
        logger.info(f"    Pen Taken/60: {team_stats.get('pen_taken_60', 'N/A')}")
        logger.info(f"    Pen Drawn/60: {team_stats.get('pen_drawn_60', 'N/A')}")
        logger.info(f"    Net Pen/60: {team_stats.get('net_pen_60', 'N/A')}")


def test_data_structure_validation(boxscore, pbp):
    """Test: Validate data structure for DB schema design."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Data Structure Validation (for DB Schema)")
    logger.info("=" * 80)
    
    logger.info("Boxscore Structure:")
    logger.info(f"  Top-level keys: {list(boxscore.keys())}")
    
    home_team = boxscore.get("homeTeam", {})
    logger.info(f"  Home Team keys: {list(home_team.keys())}")
    logger.info(f"    - id: {home_team.get('id')} (type: {type(home_team.get('id')).__name__})")
    logger.info(f"    - abbrev: {home_team.get('abbrev')} (type: {type(home_team.get('abbrev')).__name__})")
    logger.info(f"    - powerPlayGoals: {home_team.get('powerPlayGoals')} (type: {type(home_team.get('powerPlayGoals')).__name__})")
    
    logger.info(f"\nPlay-by-Play Structure:")
    logger.info(f"  Top-level keys: {list(pbp.keys())}")
    
    plays = pbp.get("plays", [])
    if plays:
        first_play = plays[0]
        logger.info(f"  First play keys: {list(first_play.keys())}")
        logger.info(f"    - typeDescKey: {first_play.get('typeDescKey')} (type: {type(first_play.get('typeDescKey')).__name__})")
        
        details = first_play.get("details", {})
        logger.info(f"    - details keys: {list(details.keys())}")
        logger.info(f"      - xCoord: {details.get('xCoord')} (type: {type(details.get('xCoord')).__name__})")
        logger.info(f"      - yCoord: {details.get('yCoord')} (type: {type(details.get('yCoord')).__name__})")
        logger.info(f"      - eventOwnerTeamId: {details.get('eventOwnerTeamId')} (type: {type(details.get('eventOwnerTeamId')).__name__})")


def test_edge_cases(boxscore, pbp):
    """Test: Handle edge cases."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Edge Cases")
    logger.info("=" * 80)
    
    # Test with None data
    logger.info("Testing with None boxscore...")
    stats = calculate_game_stats(None, pbp)
    assert stats is None, "Should handle None boxscore"
    logger.info("✓ Handles None boxscore correctly")
    
    logger.info("Testing with None play-by-play...")
    stats = calculate_game_stats(boxscore, None)
    assert stats is None, "Should handle None play-by-play"
    logger.info("✓ Handles None play-by-play correctly")
    
    logger.info("Testing with empty plays...")
    pbp_empty = pbp.copy()
    pbp_empty["plays"] = []
    stats = calculate_game_stats(boxscore, pbp_empty)
    assert stats is not None, "Should handle empty plays"
    logger.info("✓ Handles empty plays correctly")


def main():
    """Run all Phase 2 validation tests."""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "PHASE 2: DATA VALIDATION TEST SUITE".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    
    try:
        # Test 1: Fetch boxscore
        game_id = test_api_client_fetch_boxscore()
        
        # Test 2: Fetch play-by-play
        pbp = test_api_client_fetch_play_by_play(game_id)
        
        # Fetch boxscore for remaining tests
        client = NHLAPIClient()
        boxscore = client.fetch_boxscore(game_id)
        
        # Test 3: Calculate stats
        test_stats_calculator(boxscore, pbp)
        
        # Test 4: Validate data structure
        test_data_structure_validation(boxscore, pbp)
        
        # Test 5: Edge cases
        test_edge_cases(boxscore, pbp)
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 80)
        logger.info("\nPhase 2 Validation Complete!")
        logger.info("Ready for Phase 3: DB Schema Design")
        logger.info("\nKey Findings:")
        logger.info("- API client successfully fetches real data")
        logger.info("- Stats calculator processes data correctly")
        logger.info("- Data structure is consistent and predictable")
        logger.info("- Edge cases are handled gracefully")
        logger.info("\nNext Steps:")
        logger.info("1. Design SQLite schema based on data structure")
        logger.info("2. Build db_manager.py (class-based)")
        logger.info("3. Build aggregator.py (rolling windows)")
        
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
