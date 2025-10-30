"""Test Stats API for PP data."""

import requests
import json

game_id = "2025020027"
stats_api_url = f"https://statsapi.web.nhl.com/api/v1/game/{game_id}/boxscore"

print(f"Fetching from Stats API: {stats_api_url}\n")

try:
    response = requests.get(stats_api_url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        
        # Extract team stats
        teams = data.get('teams', {})
        
        for side in ['home', 'away']:
            team_data = teams.get(side, {})
            team_info = team_data.get('team', {})
            team_stats = team_data.get('teamStats', {}).get('teamSkaterStats', {})
            
            print(f"{side.upper()} TEAM: {team_info.get('abbreviation')}")
            print(f"  PP Goals: {team_stats.get('powerPlayGoals')}")
            print(f"  PP Opps: {team_stats.get('powerPlayOpportunities')}")
            print(f"  PP %: {team_stats.get('powerPlayPercentage')}")
            print()
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
