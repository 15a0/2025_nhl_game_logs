"""
NHL API Client

Centralized, robust interface to NHL API endpoints with retry logic,
timeout handling, and structured response validation.

Features:
- Config-driven base URL and parameters
- Retry with exponential backoff
- Structured response validation
- Timeout + error handling
- Type hints + docstrings
- Ready for dependency injection

Endpoints:
- /v1/gamecenter/{game_id}/boxscore
- /v1/gamecenter/{game_id}/play-by-play
- /v1/schedule/{date}
- /stats/rest/en/season

Refactored from: get_game_detail.py + get-current-season.py (v1.0 prototypes)
"""

from __future__ import annotations

import time
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """Configuration for NHL API client."""
    base_url: str = "https://api-web.nhle.com"
    timeout: int = 15
    max_retries: int = 3
    backoff_factor: float = 0.5
    retry_status_codes: tuple = (429, 500, 502, 503, 504)

    def __post_init__(self) -> None:
        if not self.base_url.startswith("http"):
            raise ValueError("base_url must include protocol (http/https)")


class NHLAPIClient:
    """
    Robust NHL API client with retry, timeout, and structured responses.
    
    Usage:
        client = NHLAPIClient()
        boxscore = client.fetch_boxscore("2025020476")
        play_by_play = client.fetch_play_by_play("2025020476")
        schedule = client.fetch_schedule_date("2025-10-28")
    """

    def __init__(self, config: Optional[APIConfig] = None):
        self.config = config or APIConfig()
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        retry = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            status_forcelist=self.config.retry_status_codes,
            allowed_methods=frozenset(['GET']),
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Internal request handler with retry and error logging."""
        url = f"{self.config.base_url}{endpoint}"
        headers = {"User-Agent": "NHL-DFS-Analytics/2.0"}
        
        try:
            logger.debug(f"GET {url}")
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"404 Not Found: {url}")
                return None
            else:
                logger.error(f"HTTP {response.status_code}: {url} | {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout after {self.config.timeout}s: {url}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection failed: {url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e} | {url}")
        
        return None

    def fetch_boxscore(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch boxscore for a given game ID.
        
        Args:
            game_id: NHL game ID (e.g., "2025020476")
        
        Returns:
            Boxscore JSON or None if failed/404
        """
        endpoint = f"/v1/gamecenter/{game_id}/boxscore"
        return self._request(endpoint)

    def fetch_play_by_play(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch play-by-play for a given game ID.
        
        Args:
            game_id: NHL game ID
        
        Returns:
            Play-by-play JSON or None
        """
        endpoint = f"/v1/gamecenter/{game_id}/play-by-play"
        return self._request(endpoint)

    def fetch_schedule_date(self, date_str: str) -> Optional[Dict[str, Any]]:
        """
        Fetch schedule for a specific date (YYYY-MM-DD).
        
        Args:
            date_str: Date in YYYY-MM-DD format
        
        Returns:
            Schedule JSON or None
        """
        endpoint = f"/v1/schedule/{date_str}"
        return self._request(endpoint)

    def fetch_current_season(self) -> Optional[str]:
        """
        Fetch current season ID from NHL stats API.
        
        Returns:
            Season ID (e.g., "20252026") or None
        """
        # Note: stats API uses different base URL
        url = "https://api.nhle.com/stats/rest/en/season"
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            if response.status_code != 200:
                logger.error(f"Error fetching season: {response.text[:300]}")
                return None
            
            data = response.json()
            seasons = data.get("data", [])
            if not seasons:
                logger.warning("No seasons returned from API")
                return None
            
            current = max(seasons, key=lambda s: s.get("id", 0))
            season_id = current.get("id")
            logger.info(f"Current season ID: {season_id}")
            return str(season_id) if season_id else None
            
        except Exception as e:
            logger.error(f"Failed to fetch season ID: {e}")
            return None

    def fetch_season_schedule(
        self,
        season_id: Optional[str] = None,
        regular_season_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch all unique game IDs for a season by looping over dates.
        
        Args:
            season_id: Season ID (e.g., "20252026"). If None, fetches current season.
            regular_season_only: If True, only return regular season games (gameType=2)
        
        Returns:
            List of game dicts with game_id, date, teams, game_state
        """
        if not season_id:
            season_id = self.fetch_current_season()
            if not season_id:
                logger.error("Could not determine season ID")
                return []
        
        # Parse season year from season_id (e.g., "20252026" -> 2025)
        year = int(str(season_id)[:4])
        start_date = datetime(year, 10, 1)
        end_date = datetime(year + 1, 5, 1)
        
        current = start_date
        seen_game_ids = set()
        all_games = []
        
        logger.info(f"Fetching schedule from {start_date.date()} to {end_date.date()}...")
        
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            schedule = self.fetch_schedule_date(date_str)
            
            if schedule:
                game_weeks = schedule.get("gameWeek", [])
                for week in game_weeks:
                    for game in week.get("games", []):
                        game_id = game.get("id")
                        game_type = game.get("gameType")
                        
                        # Filter by game type if requested
                        if regular_season_only and game_type != 2:
                            continue
                        
                        # Skip duplicates
                        if game_id in seen_game_ids:
                            continue
                        
                        seen_game_ids.add(game_id)
                        all_games.append({
                            "game_id": game_id,
                            "date": game.get("gameDate", "N/A"),
                            "away_team": game.get("awayTeam", {}).get("abbrev", "N/A"),
                            "home_team": game.get("homeTeam", {}).get("abbrev", "N/A"),
                            "game_state": game.get("gameState", "N/A")
                        })
            
            current += timedelta(days=1)
        
        logger.info(f"Found {len(all_games)} unique games for season {season_id}")
        return all_games

    def close(self) -> None:
        """Close the underlying session."""
        self.session.close()

    def __enter__(self) -> NHLAPIClient:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
