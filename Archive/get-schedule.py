import requests
import yaml
from datetime import datetime, timezone
import os

def get_config_date(config_path=None):
    """Reads a YAML config file and returns the schedule_date if present."""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}. Using today's date.")
        return None
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            if config is None:
                print("Config file is empty. Using today's date.")
                return None
            schedule_date = config.get("schedule_date")
            if schedule_date:
                print(f"Using schedule_date from config: {schedule_date}")
            return schedule_date
    except Exception as e:
        print(f"Config read failed: {e}. Using today's date.")
        return None

def resolve_schedule_date(date_override=None, config_path=None):
    """Resolves the date to use for schedule pull."""
    if date_override:
        return date_override
    config_date = get_config_date(config_path)
    if config_date:
        return config_date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"No config date found. Using today's date: {today}")
    return today

def get_current_season_id():
    """Fetches the current season ID from the NHL API."""
    url = "https://api.nhle.com/stats/rest/en/season"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Error fetching season: {response.text[:300]}")
            return None
        data = response.json()
        seasons = data.get("data", [])
        if not seasons:
            print("No seasons returned.")
            return None
        # Latest season is the current one (YYYYYYYY format)
        current_season = max(seasons, key=lambda s: s.get("id", 0))
        season_id = current_season.get("id")
        print(f"Current season ID: {season_id}")
        return season_id
    except (requests.RequestException, ValueError) as e:
        print(f"Failed to fetch season ID: {e}")
        return None

def get_season_game_ids(season_id=None):
    """Fetches all game IDs for the given season."""
    if not season_id:
        season_id = get_current_season_id()
        if not season_id:
            return []
    
    url = f"https://api-web.nhle.com/v1/schedule/{season_id}"
    try:
        response = requests.get(url, timeout=15)
        print(f"HTTP status for season schedule: {response.status_code}")
        if response.status_code != 200:
            print(f"Error body: {response.text[:300]}")
            return []
        
        data = response.json()
        game_ids = []
        for week in data.get("gameWeek", []):
            for game in week.get("games", []):
                game_id = game.get("id")
                if game_id:
                    game_ids.append({
                        "game_id": game_id,
                        "date": week.get("date"),
                        "away_team": game.get("awayTeam", {}).get("abbrev", "N/A"),
                        "home_team": game.get("homeTeam", {}).get("abbrev", "N/A"),
                        "game_state": game.get("gameState", "N/A")
                    })
        
        print(f"Found {len(game_ids)} games for season {season_id}")
        return game_ids
    
    except (requests.RequestException, ValueError) as e:
        print(f"Failed to fetch season schedule: {e}")
        return []

def get_game_stats(game_id):
    """Fetches game-level stats (boxscore) for a specific game ID."""
    url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"
    try:
        response = requests.get(url, timeout=10)
        print(f"HTTP status for game {game_id}: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching game {game_id}: {response.text[:300]}")
            return None
    except requests.RequestException as e:
        print(f"Failed to fetch stats for game {game_id}: {e}")
        return None

def print_games(games):
    """Prints a summary of each game."""
    if not games:
        print("No games found.")
        return
    for game in games:
        print(f"Game ID: {game['game_id']} | {game['away_team']} @ {game['home_team']} - {game['game_state']} - {game['date']}")

if __name__ == "__main__":
    # Get all game IDs for the current season
    game_ids = get_season_game_ids()
    print_games(game_ids[:5])  # Print first 5 games as a sample
    
    # Example: Fetch stats for the first game (if any)
    if game_ids:
        sample_game_id = game_ids[0]["game_id"]
        stats = get_game_stats(sample_game_id)
        if stats:
            print(f"Sample stats for game {sample_game_id}:")
