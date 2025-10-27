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

def get_schedule(date_str):
    """Fetches NHL games scheduled for the given date."""
    url = f"https://api-web.nhle.com/v1/schedule/{date_str}"
    try:
        response = requests.get(url, timeout=10)
        print(f"HTTP status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response keys: {list(data.keys())}")  # Debug: e.g., ['gameWeek', 'today', ...]
            print(f"Total games reported: {data.get('totalGames', 'N/A')}")  # Debug: Should be 2
            
            game_week = data.get("gameWeek", [])
            if game_week:
                games = game_week[0].get("games", [])  # Nested under first gameWeek entry
                print(f"Extracted {len(games)} games from gameWeek.")  # Debug
                return games
            else:
                print("No 'gameWeek' in response.")
                return []
        else:
            print(f"Error body: {response.text[:300]}")
            return []
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return []

def print_games(games):
    """Prints a summary of each game."""
    if not games:
        print("No games found.")
        return
    for game in games:
        away = game['awayTeam']['abbrev']
        home = game['homeTeam']['abbrev']
        state = game['gameState']
        start = game.get('startTimeUTC', 'N/A')
        
        # Optional: Add TV broadcast if available
        broadcast = ""
        media = game.get('media', {})
        if media.get('broadcast', {}).get('blackout', {}).get('nationwide', []):
            # This is messy; simplify to first US/CA channel
            us_channels = media['broadcast']['blackout']['nationwide'].get('US', [])
            if us_channels:
                broadcast = f" | TV: {us_channels[0]['streamName']}"
        
        print(f"{away} @ {home} - {state} - {start}{broadcast}")

if __name__ == "__main__":
    # You can pass a date string here manually: resolve_schedule_date("2025-10-26")
    date_to_use = resolve_schedule_date()
    print(f"Using schedule date: {date_to_use}")
    games = get_schedule(date_to_use)
    print_games(games)