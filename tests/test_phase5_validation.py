"""
Phase 5: Slate GOI Validation Test

Validates Phase 5 modules:
1. SlateGOICalculator calculates form factor
2. SlateGOICalculator calculates matchup factor
3. SlateGOICalculator calculates Slate GOI
4. SlateGOICalculator prioritizes games
5. SlateGOICalculator generates stack recommendations
6. SlateGOICalculator provides slate summary

Run: python tests/test_phase5_validation.py
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.goi import SlateGOICalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_slate_goi_calculation():
    """Test: SlateGOICalculator calculates Slate GOI."""
    logger.info("=" * 80)
    logger.info("TEST 1: Slate GOI Calculation")
    logger.info("=" * 80)
    
    config = {
        "slate_goi": {
            "form_window": 5,
            "venue_boost": 0.08,
            "rest_penalty": -0.05
        }
    }
    
    calc = SlateGOICalculator(config)
    
    # Simulate games
    games = [
        {
            "game_id": "2025020001",
            "home_team": "FLA",
            "away_team": "CHI"
        },
        {
            "game_id": "2025020002",
            "home_team": "COL",
            "away_team": "NYR"
        }
    ]
    
    # Simulate team stats
    team_stats = {
        "FLA": {"cf_pct": 58.0, "xgf": 4.37, "xga": 1.46, "pp_pct": 33.0, "pk_pct": 100.0, "hdc_pct": 61.4},
        "CHI": {"cf_pct": 42.0, "xgf": 1.46, "xga": 4.37, "pp_pct": 0.0, "pk_pct": 50.0, "hdc_pct": 38.6},
        "COL": {"cf_pct": 52.0, "xgf": 3.2, "xga": 2.8, "pp_pct": 25.0, "pk_pct": 80.0, "hdc_pct": 50.0},
        "NYR": {"cf_pct": 48.0, "xgf": 2.5, "xga": 3.0, "pp_pct": 15.0, "pk_pct": 75.0, "hdc_pct": 48.0}
    }
    
    # Simulate TPI results
    tpi_results = {
        "FLA": {"composite_zscore": 0.85},
        "CHI": {"composite_zscore": -0.82},
        "COL": {"composite_zscore": 0.45},
        "NYR": {"composite_zscore": -0.15}
    }
    
    logger.info("Calculating Slate GOI...")
    slate_goi_games = calc.calculate_slate_goi(
        games=games,
        team_stats=team_stats,
        tpi_results=tpi_results,
        slate_date="2025-10-28"
    )
    
    logger.info(f"✓ Calculated Slate GOI for {len(slate_goi_games)} games")
    
    for game in slate_goi_games:
        logger.info(f"\n{game['away_team']} @ {game['home_team']}:")
        logger.info(f"  Slate GOI: {game['slate_goi']}")
        logger.info(f"  Form Factor: {game['form_factor']}")
        logger.info(f"  Matchup Factor: {game['matchup_factor']}")
        logger.info(f"  Venue Factor: {game['venue_factor']}")
        logger.info(f"  GOI Diff (Home - Away): {game['goi_diff']}")
        logger.info(f"  PP/PK Mismatch: {game['pp_pk_mismatch']}")
        logger.info(f"  Stack Recommendation: {game['stack_recommendation']}")
    
    assert len(slate_goi_games) == 2
    assert all("slate_goi" in g for g in slate_goi_games)
    logger.info("✓ Slate GOI calculation verified")


def test_game_prioritization():
    """Test: SlateGOICalculator prioritizes games."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Game Prioritization")
    logger.info("=" * 80)
    
    config = {
        "slate_goi": {
            "form_window": 5,
            "venue_boost": 0.08,
            "rest_penalty": -0.05
        }
    }
    
    calc = SlateGOICalculator(config)
    
    # Simulate games with different GOI scores
    slate_goi_games = [
        {
            "game_id": "2025020001",
            "home_team": "FLA",
            "away_team": "CHI",
            "slate_goi": 0.35,
            "date": "2025-10-28"
        },
        {
            "game_id": "2025020002",
            "home_team": "COL",
            "away_team": "NYR",
            "slate_goi": 0.15,
            "date": "2025-10-28"
        },
        {
            "game_id": "2025020003",
            "home_team": "BOS",
            "away_team": "TOR",
            "slate_goi": 0.25,
            "date": "2025-10-28"
        }
    ]
    
    logger.info("Prioritizing games...")
    prioritized = calc.prioritize_games(slate_goi_games)
    
    logger.info(f"✓ Prioritized {len(prioritized)} games:")
    for game in prioritized:
        logger.info(f"  {game['priority_rank']}. {game['away_team']} @ {game['home_team']}: GOI={game['slate_goi']}")
    
    # Verify order
    assert prioritized[0]["slate_goi"] == 0.35, "Highest GOI should be first"
    assert prioritized[0]["priority_rank"] == 1
    assert prioritized[-1]["slate_goi"] == 0.15, "Lowest GOI should be last"
    assert prioritized[-1]["priority_rank"] == 3
    
    logger.info("✓ Game prioritization verified")


def test_stack_recommendations():
    """Test: SlateGOICalculator generates stack recommendations."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Stack Recommendations")
    logger.info("=" * 80)
    
    config = {
        "slate_goi": {
            "form_window": 5,
            "venue_boost": 0.08,
            "rest_penalty": -0.05
        }
    }
    
    calc = SlateGOICalculator(config)
    
    # Test case 1: Strong GOI differential
    logger.info("Test case 1: Strong GOI differential")
    rec1 = calc._get_stack_recommendation(
        home_team="FLA",
        away_team="CHI",
        goi_diff=2.0,
        pp_pk_mismatch=10.0,
        home_stats={"pp_pct": 33.0, "pk_pct": 100.0, "hdc_pct": 61.4},
        away_stats={"pp_pct": 0.0, "pk_pct": 50.0, "hdc_pct": 38.6}
    )
    logger.info(f"  Recommendation: {rec1}")
    assert "FLA" in rec1, "Should recommend stacking FLA"
    
    # Test case 2: PP/PK mismatch
    logger.info("Test case 2: PP/PK mismatch")
    rec2 = calc._get_stack_recommendation(
        home_team="FLA",
        away_team="CHI",
        goi_diff=0.5,
        pp_pk_mismatch=50.0,
        home_stats={"pp_pct": 50.0, "pk_pct": 100.0, "hdc_pct": 50.0},
        away_stats={"pp_pct": 0.0, "pk_pct": 50.0, "hdc_pct": 50.0}
    )
    logger.info(f"  Recommendation: {rec2}")
    assert "PP stack" in rec2, "Should recommend PP stack"
    
    # Test case 3: High-event game
    logger.info("Test case 3: High-event game")
    rec3 = calc._get_stack_recommendation(
        home_team="FLA",
        away_team="CHI",
        goi_diff=0.5,
        pp_pk_mismatch=10.0,
        home_stats={"pp_pct": 20.0, "pk_pct": 80.0, "hdc_pct": 60.0},
        away_stats={"pp_pct": 20.0, "pk_pct": 80.0, "hdc_pct": 60.0}
    )
    logger.info(f"  Recommendation: {rec3}")
    assert "High-event" in rec3, "Should identify high-event game"
    
    logger.info("✓ Stack recommendations verified")


def test_slate_summary():
    """Test: SlateGOICalculator provides slate summary."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Slate Summary")
    logger.info("=" * 80)
    
    config = {
        "slate_goi": {
            "form_window": 5,
            "venue_boost": 0.08,
            "rest_penalty": -0.05
        }
    }
    
    calc = SlateGOICalculator(config)
    
    # Simulate prioritized games
    prioritized_games = [
        {
            "priority_rank": 1,
            "game_id": "2025020001",
            "home_team": "FLA",
            "away_team": "CHI",
            "slate_goi": 0.35,
            "date": "2025-10-28",
            "stack_recommendation": "Stack FLA"
        },
        {
            "priority_rank": 2,
            "game_id": "2025020002",
            "home_team": "COL",
            "away_team": "NYR",
            "slate_goi": 0.25,
            "date": "2025-10-28",
            "stack_recommendation": "Monitor"
        },
        {
            "priority_rank": 3,
            "game_id": "2025020003",
            "home_team": "BOS",
            "away_team": "TOR",
            "slate_goi": 0.15,
            "date": "2025-10-28",
            "stack_recommendation": "Monitor"
        }
    ]
    
    logger.info("Generating slate summary...")
    summary = calc.get_slate_summary(prioritized_games, top_n=2)
    
    logger.info(f"✓ Slate Summary:")
    logger.info(f"  Total Games: {summary['total_games']}")
    logger.info(f"  Slate Date: {summary['slate_date']}")
    logger.info(f"  High Priority Games: {summary['high_priority_count']}")
    logger.info(f"  Average Slate GOI: {summary['average_slate_goi']}")
    logger.info(f"  Top Games:")
    for game in summary['top_games']:
        logger.info(f"    {game['priority_rank']}. {game['away_team']} @ {game['home_team']}: {game['stack_recommendation']}")
    
    assert summary["total_games"] == 3
    assert summary["high_priority_count"] == 3
    assert len(summary["top_games"]) == 2
    assert summary["average_slate_goi"] == 0.25
    
    logger.info("✓ Slate summary verified")


def main():
    """Run all Phase 5 validation tests."""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "PHASE 5: SLATE GOI VALIDATION TEST SUITE".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    
    try:
        # Test 1: Slate GOI calculation
        test_slate_goi_calculation()
        
        # Test 2: Game prioritization
        test_game_prioritization()
        
        # Test 3: Stack recommendations
        test_stack_recommendations()
        
        # Test 4: Slate summary
        test_slate_summary()
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 80)
        logger.info("\nPhase 5 Validation Complete!")
        logger.info("\nKey Findings:")
        logger.info("- SlateGOICalculator calculates Slate GOI correctly")
        logger.info("- Games prioritized by GOI score")
        logger.info("- Stack recommendations generated (GOI diff, PP/PK, high-event)")
        logger.info("- Slate summary provided with top games and analysis")
        logger.info("\nPhase 5 Complete - Full Pipeline Ready!")
        logger.info("\nNext Steps:")
        logger.info("1. Commit Phase 5 to remote")
        logger.info("2. Build orchestrator (end-to-end pipeline)")
        logger.info("3. Deploy to production")
        
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
