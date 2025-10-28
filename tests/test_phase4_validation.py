"""
Phase 4: Z-Score & TPI Validation Test

Validates Phase 4 modules:
1. ZScoreCalculator calculates z-scores correctly
2. ZScoreCalculator handles edge cases (None, division by zero)
3. TPICalculator calculates TPI for single team
4. TPICalculator calculates TPI for all teams
5. TPICalculator ranks teams correctly
6. TPICalculator provides summary statistics

Run: python tests/test_phase4_validation.py
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.calc import ZScoreCalculator, TPICalculator
from src.db import DBManager
from src.aggregator import StatsAggregator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_zscore_calculation():
    """Test: ZScoreCalculator calculates z-scores correctly."""
    logger.info("=" * 80)
    logger.info("TEST 1: Z-Score Calculation")
    logger.info("=" * 80)
    
    calc = ZScoreCalculator()
    
    # Simple test data
    team_stats = {
        "cf_pct": 52.0,
        "xgf": 3.0,
        "xga": 2.8,
        "pp_pct": 20.0
    }
    
    league_context = {
        "cf_pct": {"mean": 50.0, "std": 3.0},
        "xgf": {"mean": 2.8, "std": 0.5},
        "xga": {"mean": 2.8, "std": 0.5},
        "pp_pct": {"mean": 20.0, "std": 5.0}
    }
    
    logger.info("Calculating z-scores...")
    z_scores = calc.calculate_zscores(team_stats, league_context)
    
    logger.info(f"✓ Z-Scores calculated:")
    for stat, z in z_scores.items():
        logger.info(f"  {stat}: {z}")
    
    # Verify calculations
    assert z_scores["cf_pct"] == 0.67, f"Expected 0.67, got {z_scores['cf_pct']}"
    assert z_scores["xgf"] == 0.4, f"Expected 0.4, got {z_scores['xgf']}"
    assert z_scores["xga"] == 0.0, f"Expected 0.0, got {z_scores['xga']}"
    assert z_scores["pp_pct"] == 0.0, f"Expected 0.0, got {z_scores['pp_pct']}"
    
    logger.info("✓ All z-score calculations verified")


def test_zscore_edge_cases():
    """Test: ZScoreCalculator handles edge cases."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Z-Score Edge Cases")
    logger.info("=" * 80)
    
    calc = ZScoreCalculator()
    
    # Test with None value
    logger.info("Testing with None value...")
    team_stats = {"cf_pct": None, "xgf": 3.0}
    league_context = {
        "cf_pct": {"mean": 50.0, "std": 3.0},
        "xgf": {"mean": 2.8, "std": 0.5}
    }
    
    z_scores = calc.calculate_zscores(team_stats, league_context)
    assert z_scores["cf_pct"] is None, "Should handle None values"
    logger.info("✓ Handles None values correctly")
    
    # Test with zero std dev
    logger.info("Testing with zero std dev...")
    team_stats = {"cf_pct": 50.0}
    league_context = {"cf_pct": {"mean": 50.0, "std": 0}}
    
    z_scores = calc.calculate_zscores(team_stats, league_context)
    assert z_scores["cf_pct"] == 0.0, "Should handle zero std dev"
    logger.info("✓ Handles zero std dev correctly")


def test_bucket_zscores():
    """Test: ZScoreCalculator calculates bucket z-scores."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Bucket Z-Scores")
    logger.info("=" * 80)
    
    calc = ZScoreCalculator()
    
    # Individual z-scores
    z_scores = {
        "cf_pct": 0.5,
        "xgf": 1.0,
        "pp_pct": 0.0,
        "xga": -0.5,
        "pk_pct": 0.5,
        "fow_pct": 0.0
    }
    
    # Bucket definitions
    stat_buckets = {
        "offensive_creation": {
            "weight": 0.4,
            "stats": ["cf_pct", "xgf", "pp_pct"]
        },
        "defensive_resistance": {
            "weight": 0.3,
            "stats": ["xga", "pk_pct"],
            "reverse_sign": True
        },
        "pace_drivers": {
            "weight": 0.3,
            "stats": ["fow_pct"]
        }
    }
    
    logger.info("Calculating bucket z-scores...")
    bucket_zscores = calc.calculate_bucket_zscores(
        z_scores,
        stat_buckets,
        reverse_sign_stats=["xga", "pk_pct"]
    )
    
    logger.info(f"✓ Bucket Z-Scores:")
    for bucket, z in bucket_zscores.items():
        logger.info(f"  {bucket}: {z}")
    
    # Verify calculations
    # offensive_creation: (0.5 + 1.0 + 0.0) / 3 = 0.5
    assert bucket_zscores["offensive_creation"] == 0.5
    # defensive_resistance: (0.5 + -0.5) / 2 = 0.0 (with sign reversal)
    assert bucket_zscores["defensive_resistance"] == 0.0
    # pace_drivers: 0.0
    assert bucket_zscores["pace_drivers"] == 0.0
    
    logger.info("✓ All bucket calculations verified")


def test_composite_zscore():
    """Test: ZScoreCalculator calculates composite z-score."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Composite Z-Score (TPI)")
    logger.info("=" * 80)
    
    calc = ZScoreCalculator()
    
    bucket_zscores = {
        "offensive_creation": 0.5,
        "defensive_resistance": 0.0,
        "pace_drivers": 0.0
    }
    
    stat_buckets = {
        "offensive_creation": {"weight": 0.4},
        "defensive_resistance": {"weight": 0.3},
        "pace_drivers": {"weight": 0.3}
    }
    
    logger.info("Calculating composite z-score...")
    composite = calc.calculate_composite_zscore(bucket_zscores, stat_buckets)
    
    logger.info(f"✓ Composite Z-Score (TPI): {composite}")
    
    # Verify: (0.5 * 0.4 + 0.0 * 0.3 + 0.0 * 0.3) = 0.2
    assert composite == 0.2, f"Expected 0.2, got {composite}"
    logger.info("✓ Composite z-score calculation verified")


def test_tpi_single_team():
    """Test: TPICalculator calculates TPI for single team."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: TPI Calculation (Single Team)")
    logger.info("=" * 80)
    
    config = {
        "stat_buckets": {
            "offensive_creation": {
                "weight": 0.4,
                "stats": ["cf_pct", "xgf", "pp_pct"]
            },
            "defensive_resistance": {
                "weight": 0.3,
                "stats": ["xga", "pk_pct"],
                "reverse_sign": True
            },
            "pace_drivers": {
                "weight": 0.3,
                "stats": ["fow_pct"]
            }
        }
    }
    
    calc = TPICalculator(config)
    
    team_stats = {
        "cf_pct": 52.0,
        "xgf": 3.0,
        "pp_pct": 20.0,
        "xga": 2.8,
        "pk_pct": 75.0,
        "fow_pct": 51.0
    }
    
    league_context = {
        "cf_pct": {"mean": 50.0, "std": 3.0},
        "xgf": {"mean": 2.8, "std": 0.5},
        "pp_pct": {"mean": 20.0, "std": 5.0},
        "xga": {"mean": 2.8, "std": 0.5},
        "pk_pct": {"mean": 75.0, "std": 5.0},
        "fow_pct": {"mean": 50.0, "std": 2.0}
    }
    
    logger.info("Calculating TPI for single team...")
    tpi = calc.calculate_tpi(team_stats, league_context)
    
    logger.info(f"✓ TPI Results:")
    logger.info(f"  Composite Z-Score: {tpi['composite_zscore']}")
    logger.info(f"  Bucket Z-Scores: {tpi['bucket_zscores']}")
    logger.info(f"  Individual Z-Scores: {tpi['individual_zscores']}")
    
    assert "composite_zscore" in tpi
    assert "bucket_zscores" in tpi
    assert "individual_zscores" in tpi
    logger.info("✓ TPI calculation verified")


def test_tpi_all_teams():
    """Test: TPICalculator calculates TPI for all teams."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: TPI Calculation (All Teams)")
    logger.info("=" * 80)
    
    config = {
        "stat_buckets": {
            "offensive_creation": {
                "weight": 0.4,
                "stats": ["cf_pct", "xgf", "pp_pct"]
            },
            "defensive_resistance": {
                "weight": 0.3,
                "stats": ["xga", "pk_pct"],
                "reverse_sign": True
            },
            "pace_drivers": {
                "weight": 0.3,
                "stats": ["fow_pct"]
            }
        }
    }
    
    calc = TPICalculator(config)
    
    # Simulate multiple teams
    all_teams_stats = {
        "FLA": {
            "cf_pct": 58.0,
            "xgf": 4.37,
            "pp_pct": 33.0,
            "xga": 1.46,
            "pk_pct": 100.0,
            "fow_pct": 52.0
        },
        "CHI": {
            "cf_pct": 42.0,
            "xgf": 1.46,
            "pp_pct": 0.0,
            "xga": 4.37,
            "pk_pct": 50.0,
            "fow_pct": 48.0
        }
    }
    
    league_context = {
        "cf_pct": {"mean": 50.0, "std": 8.0},
        "xgf": {"mean": 2.92, "std": 1.46},
        "pp_pct": {"mean": 16.5, "std": 16.5},
        "xga": {"mean": 2.92, "std": 1.46},
        "pk_pct": {"mean": 75.0, "std": 25.0},
        "fow_pct": {"mean": 50.0, "std": 2.0}
    }
    
    logger.info("Calculating TPI for all teams...")
    tpi_results = calc.calculate_tpi_for_all_teams(all_teams_stats, league_context)
    
    logger.info(f"✓ Calculated TPI for {len(tpi_results)} teams")
    for team, tpi in tpi_results.items():
        logger.info(f"  {team}: TPI={tpi['composite_zscore']}")


def test_team_ranking():
    """Test: TPICalculator ranks teams correctly."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 7: Team Ranking")
    logger.info("=" * 80)
    
    config = {
        "stat_buckets": {
            "offensive_creation": {"weight": 0.4, "stats": ["cf_pct"]},
            "defensive_resistance": {"weight": 0.3, "stats": ["xga"], "reverse_sign": True},
            "pace_drivers": {"weight": 0.3, "stats": ["fow_pct"]}
        }
    }
    
    calc = TPICalculator(config)
    
    # Simulate TPI results
    tpi_results = {
        "FLA": {"composite_zscore": 0.85},
        "COL": {"composite_zscore": 0.72},
        "NYR": {"composite_zscore": 0.61},
        "CHI": {"composite_zscore": -0.82}
    }
    
    logger.info("Ranking teams...")
    rankings = calc.rank_teams(tpi_results)
    
    logger.info(f"✓ Team Rankings:")
    for team, tpi, rank in rankings:
        logger.info(f"  {rank}. {team}: {tpi}")
    
    # Verify ranking order
    assert rankings[0][0] == "FLA", "FLA should be ranked 1st"
    assert rankings[0][2] == 1, "FLA should have rank 1"
    assert rankings[-1][0] == "CHI", "CHI should be ranked last"
    assert rankings[-1][2] == 4, "CHI should have rank 4"
    
    logger.info("✓ Team ranking verified")


def test_tpi_summary():
    """Test: TPICalculator provides summary statistics."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 8: TPI Summary Statistics")
    logger.info("=" * 80)
    
    config = {
        "stat_buckets": {
            "offensive_creation": {"weight": 0.4, "stats": ["cf_pct"]},
            "defensive_resistance": {"weight": 0.3, "stats": ["xga"], "reverse_sign": True},
            "pace_drivers": {"weight": 0.3, "stats": ["fow_pct"]}
        }
    }
    
    calc = TPICalculator(config)
    
    tpi_results = {
        "FLA": {"composite_zscore": 0.85},
        "COL": {"composite_zscore": 0.72},
        "NYR": {"composite_zscore": 0.61},
        "CHI": {"composite_zscore": -0.82}
    }
    
    logger.info("Generating TPI summary...")
    summary = calc.get_tpi_summary(tpi_results, top_n=2)
    
    logger.info(f"✓ TPI Summary:")
    logger.info(f"  Total Teams: {summary['total_teams']}")
    logger.info(f"  Mean TPI: {summary['mean_tpi']}")
    logger.info(f"  Max TPI: {summary['max_tpi']}")
    logger.info(f"  Min TPI: {summary['min_tpi']}")
    logger.info(f"  Top Teams: {summary['top_teams']}")
    logger.info(f"  Bottom Teams: {summary['bottom_teams']}")
    
    assert summary["total_teams"] == 4
    assert summary["max_tpi"] == 0.85
    assert summary["min_tpi"] == -0.82
    assert len(summary["top_teams"]) == 2
    logger.info("✓ Summary statistics verified")


def main():
    """Run all Phase 4 validation tests."""
    logger.info("\n")
    logger.info("╔" + "=" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "PHASE 4: Z-SCORE & TPI VALIDATION TEST SUITE".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "=" * 78 + "╝")
    
    try:
        # Test 1: Z-Score calculation
        test_zscore_calculation()
        
        # Test 2: Edge cases
        test_zscore_edge_cases()
        
        # Test 3: Bucket z-scores
        test_bucket_zscores()
        
        # Test 4: Composite z-score
        test_composite_zscore()
        
        # Test 5: TPI single team
        test_tpi_single_team()
        
        # Test 6: TPI all teams
        test_tpi_all_teams()
        
        # Test 7: Team ranking
        test_team_ranking()
        
        # Test 8: Summary statistics
        test_tpi_summary()
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 80)
        logger.info("\nPhase 4 Validation Complete!")
        logger.info("\nKey Findings:")
        logger.info("- ZScoreCalculator calculates z-scores correctly")
        logger.info("- Edge cases handled (None values, division by zero)")
        logger.info("- Bucket z-scores calculated accurately")
        logger.info("- Composite z-score (TPI) calculated correctly")
        logger.info("- Teams ranked 1-32 by TPI")
        logger.info("- Summary statistics provided")
        logger.info("\nNext Steps:")
        logger.info("1. Build slate_goi_calculator.py (Phase 5)")
        logger.info("2. Integrate form, matchup, venue, rest factors")
        logger.info("3. Output game prioritization for DFS slates")
        
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
