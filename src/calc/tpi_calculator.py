"""
TPI (Team DFS Power Index) Calculator

Calculates team power index from bucketed z-scores.

TPI Formula (v2.0):
  TPI = Composite Z-Score (weighted average of 3 buckets)
  
Buckets (from config):
  - Offensive Creation (40%): CF%, xGF, PP%, etc.
  - Defensive Resistance (30%): xGA, PK%, Pen Taken/60, etc.
  - Pace Drivers (30%): FOW%, Pen Drawn/60, Net Pen/60

Output:
  TPI Ranking: Teams ranked 1-32 by composite z-score
  
Evolution (v1.0 → v2.0):
  v1.0: Manual Excel input (weekly)
  v2.0: Automatic from game-level data (nightly)

Refactored from: v1.0 tpi_calculator.py
"""

import logging
from typing import Dict, List, Tuple, Optional

from .zscore_calculator import ZScoreCalculator

logger = logging.getLogger(__name__)


class TPICalculator:
    """
    Calculate TPI (Team DFS Power Index) from z-scores.
    
    Usage:
        calc = TPICalculator(config)
        tpi_scores = calc.calculate_tpi_for_all_teams(
            all_teams_stats={"FLA": {...}, "CHI": {...}, ...},
            league_context={...}
        )
        rankings = calc.rank_teams(tpi_scores)
    """
    
    def __init__(self, config: Dict):
        """
        Initialize TPI calculator.
        
        Args:
            config: Config dict with stat_buckets definition
        """
        self.config = config
        self.stat_buckets = config.get("stat_buckets", {})
        self.zscore_calc = ZScoreCalculator()
    
    def calculate_tpi(
        self,
        team_stats: Dict[str, float],
        league_context: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Calculate TPI for a single team.
        
        Args:
            team_stats: Team's aggregated stats
                Example: {"cf_pct": 52.3, "xgf": 3.2, ...}
            league_context: League-wide mean/std for normalization
        
        Returns:
            Dict with:
              - "composite_zscore": Overall TPI value
              - "bucket_zscores": Z-scores for each bucket
              - "individual_zscores": Z-scores for each stat
        
        Example:
            >>> tpi = calc.calculate_tpi(
            ...     team_stats={"cf_pct": 52.3, "xgf": 3.2, ...},
            ...     league_context={...}
            ... )
            >>> tpi["composite_zscore"]
            0.45
        """
        # Calculate individual z-scores
        individual_zscores = self.zscore_calc.calculate_zscores(
            team_stats,
            league_context
        )
        
        # Determine which stats need sign reversal (lower is better)
        reverse_sign_stats = []
        for bucket_name, bucket_config in self.stat_buckets.items():
            if bucket_config.get("reverse_sign", False):
                reverse_sign_stats.extend(bucket_config.get("stats", []))
        
        # Calculate bucket z-scores
        bucket_zscores = self.zscore_calc.calculate_bucket_zscores(
            individual_zscores,
            self.stat_buckets,
            reverse_sign_stats=reverse_sign_stats
        )
        
        # Calculate composite z-score (TPI)
        composite_zscore = self.zscore_calc.calculate_composite_zscore(
            bucket_zscores,
            self.stat_buckets
        )
        
        return {
            "composite_zscore": composite_zscore,
            "bucket_zscores": bucket_zscores,
            "individual_zscores": individual_zscores
        }
    
    def calculate_tpi_for_all_teams(
        self,
        all_teams_stats: Dict[str, Dict[str, float]],
        league_context: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict]:
        """
        Calculate TPI for all teams.
        
        Args:
            all_teams_stats: Dict with team abbreviation as key, stats as value
                Example: {
                    "FLA": {"cf_pct": 52.3, "xgf": 3.2, ...},
                    "CHI": {"cf_pct": 48.1, "xgf": 2.8, ...},
                    ...
                }
            league_context: League-wide normalization context
        
        Returns:
            Dict with team abbreviation as key, TPI results as value
        """
        tpi_results = {}
        
        for team, stats in all_teams_stats.items():
            tpi = self.calculate_tpi(stats, league_context)
            tpi_results[team] = tpi
            logger.debug(f"{team}: TPI={tpi['composite_zscore']}")
        
        logger.info(f"Calculated TPI for {len(tpi_results)} teams")
        return tpi_results
    
    def rank_teams(
        self,
        tpi_results: Dict[str, Dict]
    ) -> List[Tuple[str, float, int]]:
        """
        Rank teams by TPI (composite z-score).
        
        Args:
            tpi_results: Dict of TPI results from calculate_tpi_for_all_teams()
        
        Returns:
            List of tuples: (team_abbrev, tpi_score, rank)
            Sorted by TPI descending (best first)
        
        Example:
            >>> rankings = calc.rank_teams(tpi_results)
            >>> for team, tpi, rank in rankings[:5]:
            ...     print(f"{rank}. {team}: {tpi}")
            1. FLA: 0.85
            2. COL: 0.72
            3. NYR: 0.61
            ...
        """
        # Extract composite z-scores
        teams_with_scores = [
            (team, results["composite_zscore"])
            for team, results in tpi_results.items()
        ]
        
        # Sort by score descending
        teams_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Add rank
        rankings = [
            (team, score, rank + 1)
            for rank, (team, score) in enumerate(teams_with_scores)
        ]
        
        return rankings
    
    def get_tpi_summary(
        self,
        tpi_results: Dict[str, Dict],
        top_n: int = 10
    ) -> Dict:
        """
        Get summary of TPI rankings.
        
        Args:
            tpi_results: Dict of TPI results
            top_n: Number of top teams to include
        
        Returns:
            Dict with summary stats and top teams
        
        Example:
            >>> summary = calc.get_tpi_summary(tpi_results, top_n=5)
            >>> summary["top_teams"]
            [("FLA", 0.85, 1), ("COL", 0.72, 2), ...]
        """
        rankings = self.rank_teams(tpi_results)
        
        # Calculate league stats
        all_scores = [results["composite_zscore"] for results in tpi_results.values()]
        
        return {
            "total_teams": len(tpi_results),
            "mean_tpi": round(sum(all_scores) / len(all_scores), 2) if all_scores else 0,
            "max_tpi": round(max(all_scores), 2) if all_scores else 0,
            "min_tpi": round(min(all_scores), 2) if all_scores else 0,
            "top_teams": rankings[:top_n],
            "bottom_teams": rankings[-top_n:],
            "all_rankings": rankings
        }
