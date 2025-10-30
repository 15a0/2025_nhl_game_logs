"""Debug PP extraction for game 2025020027."""

import requests
import json

game_id = "2025020027"
pbp_url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"

print(f"Fetching play-by-play for game {game_id}...\n")

pbp = requests.get(pbp_url, timeout=10).json()
plays = pbp.get('plays', [])

print("=" * 80)
print("ALL PENALTY EVENTS")
print("=" * 80)

penalty_count = 0
for i, play in enumerate(plays):
    if play.get('typeDescKey') == 'penalty':
        penalty_count += 1
        details = play.get('details', {})
        
        print(f"\n[{penalty_count}] Period {play.get('periodDescriptor', {}).get('number')} - {play.get('about', {}).get('periodTime')}")
        print(f"  Type Code: {details.get('typeCode')}")
        print(f"  Type: {details.get('descKey')}")
        print(f"  Duration: {details.get('duration')} min")
        print(f"  Committed By Team: {details.get('committedByTeamId')}")
        print(f"  Drawn By Team: {details.get('drawnByTeamId')}")
        print(f"  Event Owner Team: {details.get('eventOwnerTeamId')}")

print("\n" + "=" * 80)
print("ALL GOAL EVENTS (to check PP goals)")
print("=" * 80)

goal_count = 0
for i, play in enumerate(plays):
    if play.get('typeDescKey') == 'goal':
        goal_count += 1
        details = play.get('details', {})
        
        print(f"\n[{goal_count}] Period {play.get('periodDescriptor', {}).get('number')} - {play.get('about', {}).get('periodTime')}")
        print(f"  Scoring Team: {details.get('eventOwnerTeamId')}")
        print(f"  Strength: {details.get('strength', {}).get('code')}")
        print(f"  Situation Code: {play.get('situationCode')}")
        print(f"  Scorer: {details.get('scoringPlayerId')}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total penalties: {penalty_count}")
print(f"Total goals: {goal_count}")

# Now manually count PP opps for FLA (team 13)
# eventOwnerTeamId indicates who took the penalty
# If eventOwnerTeamId == 9 (OTT), then OTT took penalty → FLA gets PP opp
# If eventOwnerTeamId == 13 (FLA), then FLA took penalty → OTT gets PP opp
print("\n" + "=" * 80)
print("MANUAL PP OPP COUNT FOR FLA (team 13)")
print("=" * 80)

fla_pp_opps = 0
ott_pp_opps = 0
for play in plays:
    if play.get('typeDescKey') == 'penalty':
        details = play.get('details', {})
        penalty_type = details.get('typeCode', '')
        event_owner_team = details.get('eventOwnerTeamId')
        
        if penalty_type == 'MIN':
            if event_owner_team == 9:  # OTT took penalty
                fla_pp_opps += 1
                print(f"  FLA PP Opp #{fla_pp_opps}: {details.get('descKey')} by OTT (team 9)")
            elif event_owner_team == 13:  # FLA took penalty
                ott_pp_opps += 1
                print(f"  OTT PP Opp #{ott_pp_opps}: {details.get('descKey')} by FLA (team 13)")

print(f"\nTotal FLA PP Opps (from PBP): {fla_pp_opps}")
print(f"Total OTT PP Opps (from PBP): {ott_pp_opps}")

# Count FLA PP goals
print("\n" + "=" * 80)
print("MANUAL PP GOAL COUNT FOR FLA (team 13)")
print("=" * 80)

fla_pp_goals = 0
for play in plays:
    if play.get('typeDescKey') == 'goal':
        details = play.get('details', {})
        strength = details.get('strength', {}).get('code', '')
        
        if details.get('eventOwnerTeamId') == 13 and strength == 'PP':
            fla_pp_goals += 1
            print(f"  FLA PP Goal #{fla_pp_goals}: {play.get('about', {}).get('periodTime')}")

print(f"\nTotal FLA PP Goals (from PBP): {fla_pp_goals}")
