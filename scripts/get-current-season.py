import requests
import yaml
import json
from datetime import datetime, timezone, timedelta
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

def get_season_game_ids(season_id=None, regular_season_only=True):
    """Fetches UNIQUE game IDs for the current season by looping over dates."""
    if not season_id:
        season_id = get_current_season_id()
        if not season_id:
            return []
    
    year = int(str(season_id)[:4])
    start_date = datetime(year, 10, 1)
    end_date = datetime(year + 1, 5, 1)

    current = start_date
    seen_game_ids = set()
    all_games = []

    print(f"Fetching schedule from {start_date.date()} to {end_date.date()}...")

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        url = f"https://api-web.nhle.com/v1/schedule/{date_str}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                game_weeks = data.get("gameWeek", [])
                for week in game_weeks:
                    for game in week.get("games", []):
                        game_id = game.get("id")
                        game_type = game.get("gameType")
                        
                        if regular_season_only and game_type != 2:
                            continue
                        
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
            elif response.status_code != 404:
                print(f"Warning: HTTP {response.status_code} for {date_str}")
        except Exception as e:
            print(f"Error on {date_str}: {e}")
        
        current += timedelta(days=1)

    print(f"Found {len(all_games)} UNIQUE games for season {season_id}")
    return all_games

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

def export_games_to_csv(games, output_file="schedule.csv"):
    """Exports games to a pipe-delimited CSV file."""
    if not games:
        print("No games to export.")
        return
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("game_id|away_team|home_team|game_state|date\n")
            for game in games:
                line = f"{game['game_id']}|{game['away_team']}|{game['home_team']}|{game['game_state']}|{game['date']}\n"
                f.write(line)
        print(f"Exported {len(games)} games to {output_file}")
    except Exception as e:
        print(f"Error exporting to CSV: {e}")

def save_cache(games, cache_file="game_ids_cache.json"):
    """Saves game IDs to a JSON cache file."""
    try:
        with open(cache_file, "w") as f:
            json.dump(games, f)
        print(f"Cache saved to {cache_file}")
    except Exception as e:
        print(f"Error saving cache: {e}")

def load_cache(cache_file="game_ids_cache.json"):
    """Loads game IDs from cache if it exists."""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                games = json.load(f)
                print(f"Loaded {len(games)} games from cache.")
                return games
        except Exception as e:
            print(f"Error loading cache: {e}")
    return None

if __name__ == "__main__":
    # Try cache first
    game_ids = load_cache()
    if not game_ids:
        game_ids = get_season_game_ids(regular_season_only=True)
        save_cache(game_ids)
    
    print_games(game_ids[:5])
    export_games_to_csv(game_ids, output_file="schedule.csv")
    
    if game_ids:
        sample_game_id = game_ids[0]["game_id"]
        stats = get_game_stats(sample_game_id)
        if stats:
            print(f"\nSample stats for game {sample_game_id}:")
            print(f"Home: {stats.get('homeTeam', {}).get('name', {}).get('default', 'N/A')}")
            print(f"Away: {stats.get('awayTeam', {}).get('name', {}).get('default', 'N/A')}")
            print(f"Goals: {stats.get('homeTeam', {}).get('score', 0)} - {stats.get('awayTeam', {}).get('score', 0)}")