"""Debug script to inspect boxscore structure."""

import requests
import json

game_id = '2025020001'
url = f'https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore'

print(f"Fetching boxscore for game {game_id}...\n")

try:
    response = requests.get(url, timeout=10)
    boxscore = response.json()
    
    # Get FLA (home team)
    fla = boxscore.get('homeTeam', {})
    
    print("=" * 70)
    print("FLA BOXSCORE - Power Play Fields")
    print("=" * 70)
    
    pp_fields = {
        'powerPlayGoals': fla.get('powerPlayGoals'),
        'powerPlayOpportunities': fla.get('powerPlayOpportunities'),
        'powerPlayGoalsAgainst': fla.get('powerPlayGoalsAgainst'),
        'powerPlayOpportunitiesAgainst': fla.get('powerPlayOpportunitiesAgainst')
    }
    
    print(json.dumps(pp_fields, indent=2))
    
    print("\n" + "=" * 70)
    print("FLA BOXSCORE - All Top-Level Keys")
    print("=" * 70)
    print(json.dumps(list(fla.keys()), indent=2))
    
    print("\n" + "=" * 70)
    print("FULL BOXSCORE - Top-Level Keys")
    print("=" * 70)
    print(json.dumps(list(boxscore.keys()), indent=2))
    
    print("\n" + "=" * 70)
    print("FULL BOXSCORE - teamStats (if exists)")
    print("=" * 70)
    if 'teamStats' in boxscore:
        print(json.dumps(boxscore['teamStats'], indent=2)[:2000])
    else:
        print("No teamStats found")
    
    print("\n" + "=" * 70)
    print("FULL BOXSCORE - Full Data (first 3000 chars)")
    print("=" * 70)
    print(json.dumps(boxscore, indent=2)[:3000])
    
except Exception as e:
    print(f"Error: {e}")
