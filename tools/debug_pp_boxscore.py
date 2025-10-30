"""Check PP goals in boxscore player stats."""

import requests
import json

game_id = "2025020027"
boxscore_url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"

print(f"Fetching boxscore for game {game_id}...\n")

boxscore = requests.get(boxscore_url, timeout=10).json()

# Get FLA players
player_stats = boxscore.get('playerByGameStats', {})
fla_players = player_stats.get('homeTeam', {})

print("=" * 80)
print("FLA PLAYER PP GOALS (from boxscore)")
print("=" * 80)

total_pp_goals = 0
for position in ['forwards', 'defensemen', 'goalies']:
    players = fla_players.get(position, [])
    for player in players:
        pp_goals = player.get('powerPlayGoals', 0)
        if pp_goals > 0:
            name = player.get('name', {}).get('default', 'Unknown')
            print(f"  {name}: {pp_goals} PP goal(s)")
            total_pp_goals += pp_goals

print(f"\nTotal PP Goals (boxscore): {total_pp_goals}")

# Now check play-by-play for PP goals
print("\n" + "=" * 80)
print("FLA PP GOALS (from play-by-play)")
print("=" * 80)

pbp_url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
pbp = requests.get(pbp_url, timeout=10).json()
plays = pbp.get('plays', [])

fla_pp_goals_pbp = 0
for play in plays:
    if play.get('typeDescKey') == 'goal':
        details = play.get('details', {})
        situation_code = play.get('situationCode', '')
        
        # FLA is team 13
        if details.get('eventOwnerTeamId') == 13 and situation_code in ['1451', '1351', '1341', '1241']:
            fla_pp_goals_pbp += 1
            scorer_id = details.get('scoringPlayerId')
            period = play.get('periodDescriptor', {}).get('number')
            time = play.get('about', {}).get('periodTime')
            print(f"  Goal #{fla_pp_goals_pbp}: Period {period}, Time {time}, Situation {situation_code}")

print(f"\nTotal PP Goals (play-by-play): {fla_pp_goals_pbp}")

print("\n" + "=" * 80)
print("DISCREPANCY")
print("=" * 80)
print(f"Boxscore says: {total_pp_goals} PP goals")
print(f"Play-by-play says: {fla_pp_goals_pbp} PP goals")
print(f"NHL.com says: 3 PP goals")
