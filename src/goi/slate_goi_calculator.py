"""
Slate GOI (Game Optimized Index) Calculator

Calculates game-specific GOI for DFS slate prioritization.

Slate GOI Formula (v2.0):
  Slate GOI = 0.4 × Last5_Form 
            + 0.3 × Matchup_Quality 
            + 0.2 × Venue_Factor 
            + 0.1 × Rest_Factor

Factors:
  - Last 5 Games (40%): Recent form (hot/cold streaks)
  - Matchup Quality (30%): Opponent defensive weakness
  - Venue (20%): Home/road advantage (+8% xGF for home)
  - Rest (10%): Back-to-back penalty (-3-7%)

Output:
  - Game prioritization (which games to target)
  - Stack recommendations (which teams to stack)
  - Mismatch alerts (PP% vs PK%, high-event games)

Evolution (v1.0 → v2.0):
  v1.0: Season-long GOI (static)
  v2.0: Slate-specific GOI (dynamic, updated nightly)

Refactored from: v1.0 goi_rankings.py + next_steps.md strategy
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SlateGOICalculator:
    """
    Calculate Slate GOI for game prioritization in DFS slates.
    
    Usage:
        calc = SlateGOICalculator(config)
        slate_goi = calc.calculate_slate_goi(
            games=[...],
            team_stats={...},
            tpi_results={...}
        )
        prioritized = calc.prioritize_games(slate_goi)
    """
    
    def __init__(self, config: Dict):
        """
        Initialize Slate GOI calculator.
        
        Args:
            config: Config dict with slate_goi parameters
        """
        self.config = config
        self.slate_config = config.get("slate_goi", {})
        self.form_window = self.slate_config.get("form_window", 5)
        self.venue_boost = self.slate_config.get("venue_boost", 0.08)
        self.rest_penalty = self.slate_config.get("rest_penalty", -0.05)
    
    def calculate_slate_goi(
        self,
        games: List[Dict],
        team_stats: Dict[str, Dict],
        tpi_results: Dict[str, Dict],
        slate_date: str
    ) -> List[Dict]:
        """
        Calculate Slate GOI for all games on a given date.
        
        Args:
            games: List of games for the slate
                Example: [
                    {"game_id": "2025020001", "home_team": "FLA", "away_team": "CHI", ...},
                    ...
                ]
            team_stats: Team stats dict (from aggregator)
                Example: {
                    "FLA": {"cf_pct": 58.0, "xgf": 4.37, ...},
                    "CHI": {"cf_pct": 42.0, "xgf": 1.46, ...}
                }
            tpi_results: TPI results dict (from tpi_calculator)
                Example: {
                    "FLA": {"composite_zscore": 0.85, ...},
                    "CHI": {"composite_zscore": -0.82, ...}
                }
            slate_date: Date of slate (YYYY-MM-DD)
        
        Returns:
            List of games with Slate GOI scores and analysis
        """
        slate_goi_games = []
        
        for game in games:
            home_team = game.get("home_team")
            away_team = game.get("away_team")
            game_id = game.get("game_id")
            
            if not home_team or not away_team:
                logger.warning(f"Skipping game {game_id}: missing team info")
                continue
            
            # Get team stats
            home_stats = team_stats.get(home_team, {})
            away_stats = team_stats.get(away_team, {})
            
            # Get TPI scores
            home_tpi = tpi_results.get(home_team, {}).get("composite_zscore", 0)
            away_tpi = tpi_results.get(away_team, {}).get("composite_zscore", 0)
            
            # Calculate factors
            form_factor = self._calculate_form_factor(home_stats, away_stats)
            matchup_factor = self._calculate_matchup_factor(home_stats, away_stats)
            venue_factor = self.venue_boost  # Home team advantage
            rest_factor = self._calculate_rest_factor(game)  # TBD: needs game history
            
            # Calculate Slate GOI
            slate_goi = (
                0.4 * form_factor +
                0.3 * matchup_factor +
                0.2 * venue_factor +
                0.1 * rest_factor
            )
            
            # Calculate GOI differential (home - away)
            goi_diff = home_tpi - away_tpi
            
            # Analyze matchups
            home_pp = home_stats.get("pp_pct", 0)
            away_pk = away_stats.get("pk_pct", 0)
            pp_pk_mismatch = home_pp - away_pk
            
            slate_goi_games.append({
                "game_id": game_id,
                "date": slate_date,
                "home_team": home_team,
                "away_team": away_team,
                "home_tpi": round(home_tpi, 2),
                "away_tpi": round(away_tpi, 2),
                "goi_diff": round(goi_diff, 2),
                "form_factor": round(form_factor, 2),
                "matchup_factor": round(matchup_factor, 2),
                "venue_factor": round(venue_factor, 2),
                "rest_factor": round(rest_factor, 2),
                "slate_goi": round(slate_goi, 2),
                "pp_pk_mismatch": round(pp_pk_mismatch, 2),
                "home_cf_pct": home_stats.get("cf_pct"),
                "away_cf_pct": away_stats.get("cf_pct"),
                "home_xgf": home_stats.get("xgf"),
                "away_xgf": away_stats.get("xgf"),
                "stack_recommendation": self._get_stack_recommendation(
                    home_team, away_team, goi_diff, pp_pk_mismatch, home_stats, away_stats
                )
            })
        
        return slate_goi_games
    
    def prioritize_games(
        self,
        slate_goi_games: List[Dict]
    ) -> List[Dict]:
        """
        Prioritize games by Slate GOI score.
        
        Args:
            slate_goi_games: List of games with Slate GOI scores
        
        Returns:
            Games sorted by priority (highest Slate GOI first)
        """
        # Sort by Slate GOI descending
        prioritized = sorted(
            slate_goi_games,
            key=lambda x: x["slate_goi"],
            reverse=True
        )
        
        # Add priority rank
        for rank, game in enumerate(prioritized, 1):
            game["priority_rank"] = rank
        
        return prioritized
    
    def _calculate_form_factor(
        self,
        home_stats: Dict,
        away_stats: Dict
    ) -> float:
        """
        Calculate form factor (last 5 games performance).
        
        Uses CF% and xGF as proxies for recent form.
        """
        home_cf = home_stats.get("cf_pct", 50)
        away_cf = away_stats.get("cf_pct", 50)
        
        # Normalize to 0-1 range (50% = 0.5)
        home_form = (home_cf - 40) / 20  # 40-60% → 0-1
        away_form = (away_cf - 40) / 20
        
        # Clamp to 0-1
        home_form = max(0, min(1, home_form))
        away_form = max(0, min(1, away_form))
        
        # Return home advantage
        return home_form - away_form
    
    def _calculate_matchup_factor(
        self,
        home_stats: Dict,
        away_stats: Dict
    ) -> float:
        """
        Calculate matchup factor (opponent quality).
        
        Uses xGA (opponent's xGA = home team's advantage).
        """
        home_xga_allowed = away_stats.get("xga", 2.8)  # What home team allows
        away_xga_allowed = home_stats.get("xga", 2.8)  # What away team allows
        
        # Normalize to 0-1 range (2.8 = 0.5)
        home_matchup = (3.5 - home_xga_allowed) / 2  # Lower xGA allowed = better matchup
        away_matchup = (3.5 - away_xga_allowed) / 2
        
        # Clamp to 0-1
        home_matchup = max(0, min(1, home_matchup))
        away_matchup = max(0, min(1, away_matchup))
        
        # Return home advantage
        return home_matchup - away_matchup
    
    def _calculate_rest_factor(self, game: Dict) -> float:
        """
        Calculate rest factor (back-to-back penalty).
        
        TBD: Requires game history to determine if team played yesterday.
        For now, returns 0 (neutral).
        """
        # TODO: Implement when game history is available
        return 0.0
    
    def _get_stack_recommendation(
        self,
        home_team: str,
        away_team: str,
        goi_diff: float,
        pp_pk_mismatch: float,
        home_stats: Dict,
        away_stats: Dict
    ) -> str:
        """
        Generate stack recommendation based on game analysis.
        
        Returns:
            Stack recommendation string
        """
        recommendations = []
        
        # GOI-based recommendation
        if goi_diff > 1.5:
            recommendations.append(f"Stack {home_team} (GOI +{goi_diff:.1f})")
        elif goi_diff < -1.5:
            recommendations.append(f"Stack {away_team} (GOI +{abs(goi_diff):.1f})")
        
        # PP/PK mismatch
        if pp_pk_mismatch > 15:
            recommendations.append(f"{home_team} PP stack (PP% {home_stats.get('pp_pct', 0):.0f}% vs PK% {away_stats.get('pk_pct', 0):.0f}%)")
        elif pp_pk_mismatch < -15:
            recommendations.append(f"{away_team} PP stack (PP% {away_stats.get('pp_pct', 0):.0f}% vs PK% {home_stats.get('pk_pct', 0):.0f}%)")
        
        # High-event game
        home_hdc = home_stats.get("hdc_pct", 50)
        away_hdc = away_stats.get("hdc_pct", 50)
        if home_hdc > 55 and away_hdc > 55:
            recommendations.append("High-event game (both teams >55% HDC%)")
        
        return " | ".join(recommendations) if recommendations else "Monitor"
    
    def get_slate_summary(
        self,
        prioritized_games: List[Dict],
        top_n: int = 3
    ) -> Dict:
        """
        Get summary of slate recommendations.
        
        Args:
            prioritized_games: Prioritized games list
            top_n: Number of top games to highlight
        
        Returns:
            Summary dict with top games and analysis
        """
        return {
            "total_games": len(prioritized_games),
            "slate_date": prioritized_games[0].get("date") if prioritized_games else None,
            "top_games": prioritized_games[:top_n],
            "all_games": prioritized_games,
            "high_priority_count": len([g for g in prioritized_games if g["priority_rank"] <= 3]),
            "average_slate_goi": round(
                sum(g["slate_goi"] for g in prioritized_games) / len(prioritized_games),
                2
            ) if prioritized_games else 0
        }
