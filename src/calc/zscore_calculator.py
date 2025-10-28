"""
Z-Score Calculator

Normalizes team stats using league-wide context (mean/std dev).

Z-Score Formula:
  z = (value - mean) / std_dev

Interpretation:
  z = 0   → League average
  z = 1   → 1 std dev above average (top 16%)
  z = -1  → 1 std dev below average (bottom 16%)
  z = 2   → 2 std dev above average (top 2%)

Used for:
- TPI calculation (bucketed z-scores)
- GOI calculation (season vs. rolling z-scores)
- League-wide comparison

Refactored from: v1.0 calc_zscores_v2a.py
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ZScoreCalculator:
    """
    Calculate z-scores for team stats using league context.
    
    Usage:
        calc = ZScoreCalculator()
        z_scores = calc.calculate_zscores(
            team_stats={"cf_pct": 52.3, "xgf": 3.2, ...},
            league_context={"cf_pct": {"mean": 50.0, "std": 3.2}, ...}
        )
    """
    
    def __init__(self):
        """Initialize z-score calculator."""
        pass
    
    def calculate_zscores(
        self,
        team_stats: Dict[str, float],
        league_context: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Calculate z-scores for all stats in team_stats.
        
        Args:
            team_stats: Dict with stat names and values
                Example: {"cf_pct": 52.3, "xgf": 3.2, "xga": 2.8, ...}
            league_context: Dict with league mean/std for each stat
                Example: {
                    "cf_pct": {"mean": 50.0, "std": 3.2},
                    "xgf": {"mean": 2.8, "std": 0.5},
                    ...
                }
        
        Returns:
            Dict with z-scores for each stat
            Example: {"cf_pct": 0.72, "xgf": 0.8, "xga": 0.0, ...}
        """
        z_scores = {}
        
        for stat_name, stat_value in team_stats.items():
            if stat_value is None:
                z_scores[stat_name] = None
                continue
            
            if stat_name not in league_context:
                logger.warning(f"Stat {stat_name} not in league context, skipping")
                z_scores[stat_name] = None
                continue
            
            context = league_context[stat_name]
            mean = context.get("mean")
            std = context.get("std")
            
            if mean is None or std is None:
                logger.warning(f"Missing mean/std for {stat_name}")
                z_scores[stat_name] = None
                continue
            
            # Avoid division by zero
            if std == 0:
                z_scores[stat_name] = 0.0
            else:
                z_score = (stat_value - mean) / std
                z_scores[stat_name] = round(z_score, 2)
        
        return z_scores
    
    def calculate_average_zscore(
        self,
        z_scores: Dict[str, float],
        stats_to_include: Optional[list] = None,
        reverse_sign_stats: Optional[list] = None
    ) -> float:
        """
        Calculate average z-score across multiple stats.
        
        Args:
            z_scores: Dict of z-scores
            stats_to_include: List of stat names to include (default: all)
            reverse_sign_stats: List of stats where lower is better (xGA, PK%, etc.)
                These will have their sign flipped
        
        Returns:
            Average z-score
        
        Example:
            >>> z_scores = {"cf_pct": 0.5, "xgf": 1.0, "xga": -0.5}
            >>> calc.calculate_average_zscore(
            ...     z_scores,
            ...     stats_to_include=["cf_pct", "xgf", "xga"],
            ...     reverse_sign_stats=["xga"]
            ... )
            0.67  # (0.5 + 1.0 + 0.5) / 3
        """
        if not z_scores:
            return 0.0
        
        reverse_sign_stats = reverse_sign_stats or []
        
        # Determine which stats to include
        if stats_to_include is None:
            stats_to_include = list(z_scores.keys())
        
        # Collect valid z-scores
        valid_scores = []
        for stat in stats_to_include:
            if stat not in z_scores:
                continue
            
            z_score = z_scores[stat]
            if z_score is None:
                continue
            
            # Flip sign for "lower is better" stats
            if stat in reverse_sign_stats:
                z_score = -z_score
            
            valid_scores.append(z_score)
        
        if not valid_scores:
            return 0.0
        
        avg = sum(valid_scores) / len(valid_scores)
        return round(avg, 2)
    
    def calculate_bucket_zscores(
        self,
        z_scores: Dict[str, float],
        stat_buckets: Dict[str, Dict],
        reverse_sign_stats: Optional[list] = None
    ) -> Dict[str, float]:
        """
        Calculate average z-score for each bucket.
        
        Args:
            z_scores: Dict of z-scores
            stat_buckets: Config dict with bucket definitions
                Example: {
                    "offensive_creation": {
                        "weight": 0.4,
                        "stats": ["cf_pct", "xgf", "pp_pct", ...]
                    },
                    "defensive_resistance": {
                        "weight": 0.3,
                        "stats": ["xga", "pk_pct", ...]
                    },
                    ...
                }
            reverse_sign_stats: List of stats where lower is better
        
        Returns:
            Dict with bucket names and average z-scores
            Example: {
                "offensive_creation": 0.45,
                "defensive_resistance": -0.2,
                "pace_drivers": 0.1
            }
        """
        bucket_zscores = {}
        reverse_sign_stats = reverse_sign_stats or []
        
        for bucket_name, bucket_config in stat_buckets.items():
            stats_in_bucket = bucket_config.get("stats", [])
            
            avg_z = self.calculate_average_zscore(
                z_scores,
                stats_to_include=stats_in_bucket,
                reverse_sign_stats=reverse_sign_stats
            )
            
            bucket_zscores[bucket_name] = avg_z
        
        return bucket_zscores
    
    def calculate_composite_zscore(
        self,
        bucket_zscores: Dict[str, float],
        stat_buckets: Dict[str, Dict]
    ) -> float:
        """
        Calculate composite z-score from bucket z-scores.
        
        Weighted average using bucket weights from config.
        
        Args:
            bucket_zscores: Dict of bucket z-scores
            stat_buckets: Config dict with bucket weights
        
        Returns:
            Composite z-score
        
        Example:
            >>> bucket_zscores = {
            ...     "offensive_creation": 0.5,
            ...     "defensive_resistance": -0.2,
            ...     "pace_drivers": 0.1
            ... }
            >>> stat_buckets = {
            ...     "offensive_creation": {"weight": 0.4, ...},
            ...     "defensive_resistance": {"weight": 0.3, ...},
            ...     "pace_drivers": {"weight": 0.3, ...}
            ... }
            >>> calc.calculate_composite_zscore(bucket_zscores, stat_buckets)
            0.23  # (0.5*0.4 + -0.2*0.3 + 0.1*0.3)
        """
        total_weight = 0
        weighted_sum = 0
        
        for bucket_name, z_score in bucket_zscores.items():
            if bucket_name not in stat_buckets:
                continue
            
            weight = stat_buckets[bucket_name].get("weight", 0)
            weighted_sum += z_score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        composite = weighted_sum / total_weight
        return round(composite, 2)
