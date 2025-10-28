"""
Stats Aggregator

Aggregates per-game stats into:
- Season totals (all games to date)
- Rolling windows (last N games)
- Date ranges (custom)

Used for TPI/GOI calculations which require:
- Season z-scores (baseline)
- Last 5-game z-scores (form)
- League-wide context (all 32 teams)

Refactored from: get-current-season.py aggregation logic
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StatsAggregator:
    """
    Aggregates per-game stats into rolling windows and season totals.
    
    Usage:
        agg = StatsAggregator(db_manager)
        season_stats = agg.get_season_stats("FLA", "2025-10-01", "2025-10-31")
        last_5_stats = agg.get_rolling_stats("FLA", "2025-10-31", games=5)
    """
    
    def __init__(self, db_manager):
        """
        Initialize aggregator.
        
        Args:
            db_manager: DBManager instance for querying stats
        """
        self.db = db_manager
    
    def get_season_stats(
        self,
        team: str,
        start_date: str,
        end_date: str
    ) -> Optional[Dict[str, float]]:
        """
        Get aggregated season stats for a team over a date range.
        
        Args:
            team: Team abbreviation (e.g., "FLA")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Dict with aggregated stats (averages), or None if no games
        
        Example:
            >>> agg.get_season_stats("FLA", "2025-10-01", "2025-10-31")
            {
                'games_count': 10,
                'cf_pct_avg': 52.3,
                'xgf_avg': 3.2,
                ...
            }
        """
        stats_list = self.db.query_team_stats(team, start_date, end_date, limit=1000)
        
        if not stats_list:
            logger.warning(f"No stats found for {team} between {start_date} and {end_date}")
            return None
        
        return self._aggregate_stats(stats_list, team, "season", len(stats_list))
    
    def get_rolling_stats(
        self,
        team: str,
        end_date: str,
        games: int = 5
    ) -> Optional[Dict[str, float]]:
        """
        Get aggregated stats for last N games.
        
        Args:
            team: Team abbreviation
            end_date: End date (YYYY-MM-DD)
            games: Number of games to include (default: 5)
        
        Returns:
            Dict with aggregated stats (averages), or None if fewer than N games
        
        Example:
            >>> agg.get_rolling_stats("FLA", "2025-10-31", games=5)
            {
                'games_count': 5,
                'cf_pct_avg': 54.1,
                'xgf_avg': 3.5,
                ...
            }
        """
        # Query more than needed to ensure we get exactly N games
        stats_list = self.db.query_team_stats(team, limit=games + 10)
        
        if not stats_list:
            logger.warning(f"No stats found for {team}")
            return None
        
        # Filter to games on or before end_date
        filtered = [s for s in stats_list if s['date'] <= end_date]
        
        if not filtered:
            logger.warning(f"No stats found for {team} on or before {end_date}")
            return None
        
        # Take last N games
        last_n = filtered[:games]
        
        if len(last_n) < games:
            logger.warning(f"Only {len(last_n)} games found for {team}, requested {games}")
        
        return self._aggregate_stats(last_n, team, f"last_{games}", len(last_n))
    
    def get_all_teams_season_stats(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Get season stats for all teams in database.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Dict with team abbreviation as key, aggregated stats as value
        
        Example:
            >>> agg.get_all_teams_season_stats("2025-10-01", "2025-10-31")
            {
                'FLA': {'games_count': 10, 'cf_pct_avg': 52.3, ...},
                'CHI': {'games_count': 10, 'cf_pct_avg': 48.1, ...},
                ...
            }
        """
        teams = self.db.get_team_list()
        result = {}
        
        for team in teams:
            stats = self.get_season_stats(team, start_date, end_date)
            if stats:
                result[team] = stats
        
        logger.info(f"Aggregated season stats for {len(result)} teams")
        return result
    
    def get_all_teams_rolling_stats(
        self,
        end_date: str,
        games: int = 5
    ) -> Dict[str, Dict[str, float]]:
        """
        Get rolling stats for all teams.
        
        Args:
            end_date: End date (YYYY-MM-DD)
            games: Number of games to include
        
        Returns:
            Dict with team abbreviation as key, aggregated stats as value
        """
        teams = self.db.get_team_list()
        result = {}
        
        for team in teams:
            stats = self.get_rolling_stats(team, end_date, games)
            if stats:
                result[team] = stats
        
        logger.info(f"Aggregated rolling stats ({games} games) for {len(result)} teams")
        return result
    
    def _aggregate_stats(
        self,
        stats_list: List[Dict],
        team: str,
        window: str,
        games_count: int
    ) -> Dict[str, float]:
        """
        Aggregate a list of stat dicts into averages.
        
        Args:
            stats_list: List of stat dicts from database
            team: Team abbreviation
            window: Window type (e.g., "season", "last_5")
            games_count: Number of games
        
        Returns:
            Dict with aggregated stats
        """
        if not stats_list:
            return None
        
        # Stats to aggregate (all numeric columns)
        stat_columns = [
            'pp_pct', 'pk_pct', 'fow_pct',
            'cf_pct', 'scf_pct', 'hdc_pct', 'hdco_pct', 'hdf_pct',
            'xgf', 'xga', 'pen_taken_60', 'pen_drawn_60', 'net_pen_60'
        ]
        
        aggregated = {
            'team': team,
            'window': window,
            'games_count': games_count
        }
        
        # Calculate averages
        for col in stat_columns:
            values = [s.get(col) for s in stats_list if s.get(col) is not None]
            if values:
                aggregated[f'{col}_avg'] = round(sum(values) / len(values), 2)
            else:
                aggregated[f'{col}_avg'] = None
        
        return aggregated
    
    def get_league_context(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Get league-wide stats for z-score normalization.
        
        Calculates mean and std dev for each stat across all teams.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Dict with stat names as keys, {'mean': X, 'std': Y} as values
        
        Example:
            >>> agg.get_league_context("2025-10-01", "2025-10-31")
            {
                'cf_pct': {'mean': 50.0, 'std': 3.2},
                'xgf': {'mean': 2.8, 'std': 0.5},
                ...
            }
        """
        all_teams_stats = self.get_all_teams_season_stats(start_date, end_date)
        
        if not all_teams_stats:
            logger.warning("No stats available for league context")
            return {}
        
        stat_columns = [
            'pp_pct', 'pk_pct', 'fow_pct',
            'cf_pct', 'scf_pct', 'hdc_pct', 'hdco_pct', 'hdf_pct',
            'xgf', 'xga', 'pen_taken_60', 'pen_drawn_60', 'net_pen_60'
        ]
        
        league_context = {}
        
        for col in stat_columns:
            values = [
                stats.get(f'{col}_avg')
                for stats in all_teams_stats.values()
                if stats.get(f'{col}_avg') is not None
            ]
            
            if values:
                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                std = variance ** 0.5
                
                league_context[col] = {
                    'mean': round(mean, 2),
                    'std': round(std, 2),
                    'count': len(values)
                }
        
        logger.info(f"Calculated league context for {len(league_context)} stats")
        return league_context
