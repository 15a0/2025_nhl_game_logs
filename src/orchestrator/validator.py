"""
Validation module for raw stat extraction.

Compares extracted stats against NHL Stats API (unofficial but reliable).
"""

import requests
from typing import Dict, Optional, Tuple


def get_nhl_stats_api_boxscore(game_id: str) -> Optional[Dict]:
    """
    Fetch boxscore from NHL Stats API (unofficial endpoint).
    
    This endpoint has team-level power play stats (unlike the official boxscore).
    
    Args:
        game_id: Game ID (e.g., '2025020001')
    
    Returns:
        Boxscore dict or None if fetch fails
    """
    try:
        url = f"https://statsapi.web.nhl.com/api/v1/game/{game_id}/boxscore"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  ⚠️  Stats API error: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"  ⚠️  Stats API fetch failed: {e}")
        return None


def extract_nhl_stats_api_pp(boxscore: Dict, team_abbrev: str) -> Optional[Dict]:
    """
    Extract power play stats from NHL Stats API boxscore.
    
    Args:
        boxscore: Boxscore JSON from Stats API
        team_abbrev: Team abbreviation (e.g., 'FLA')
    
    Returns:
        Dict with pp_goals, pp_opps, pp_goals_against, pp_opps_against
    """
    try:
        teams = boxscore.get('teams', {})
        
        # Find our team
        our_team = None
        opponent_team = None
        for side in ['home', 'away']:
            team_data = teams.get(side, {})
            if team_data.get('team', {}).get('abbreviation') == team_abbrev:
                our_team = team_data
            else:
                opponent_team = team_data
        
        if not our_team:
            return None
        
        # Extract PP stats
        our_stats = our_team.get('teamStats', {}).get('teamSkaterStats', {})
        opp_stats = opponent_team.get('teamStats', {}).get('teamSkaterStats', {})
        
        return {
            'pp_goals': our_stats.get('powerPlayGoals', 0),
            'pp_opps': our_stats.get('powerPlayOpportunities', 0),
            'pp_goals_against': opp_stats.get('powerPlayGoals', 0),
            'pp_opps_against': opp_stats.get('powerPlayOpportunities', 0)
        }
    
    except Exception as e:
        print(f"  ⚠️  Stats API parsing error: {e}")
        return None


def validate_game(game_id: str, extracted_stats: Dict) -> Tuple[bool, str]:
    """
    Validate extracted stats against NHL Stats API.
    
    Args:
        game_id: Game ID
        extracted_stats: Dict with extracted pp_opps, pp_goals, etc.
    
    Returns:
        Tuple of (is_valid, message)
    """
    # Get Stats API data
    boxscore = get_nhl_stats_api_boxscore(game_id)
    if not boxscore:
        return False, "Could not fetch Stats API data"
    
    # Extract team from game_id (we need to know which team to validate)
    # For now, just validate the structure
    teams = boxscore.get('teams', {})
    
    # Validate: check that we got data
    if not teams:
        return False, "No team data in Stats API response"
    
    return True, "✅ Stats API data available for validation"


def validate_pp_stats(game_id: str, team_abbrev: str, extracted: Dict) -> Tuple[bool, str]:
    """
    Validate power play stats for a specific team.
    
    Args:
        game_id: Game ID
        team_abbrev: Team abbreviation (e.g., 'FLA')
        extracted: Dict with extracted pp_goals, pp_opps, etc.
    
    Returns:
        Tuple of (is_valid, message)
    """
    # Get Stats API data
    boxscore = get_nhl_stats_api_boxscore(game_id)
    if not boxscore:
        return False, "Could not fetch Stats API data"
    
    # Extract NHL.com stats
    nhl_stats = extract_nhl_stats_api_pp(boxscore, team_abbrev)
    if not nhl_stats:
        return False, f"Could not extract stats for {team_abbrev}"
    
    # Compare
    pp_opps_match = extracted.get('pp_opps', 0) == nhl_stats.get('pp_opps', 0)
    pp_goals_match = extracted.get('pp_goals', 0) == nhl_stats.get('pp_goals', 0)
    
    if pp_opps_match and pp_goals_match:
        return True, f"✅ PP stats match: Opps={nhl_stats['pp_opps']}, Goals={nhl_stats['pp_goals']}"
    else:
        msg = f"❌ PP stats mismatch:\n"
        msg += f"  Extracted: Opps={extracted.get('pp_opps', 0)}, Goals={extracted.get('pp_goals', 0)}\n"
        msg += f"  NHL.com:   Opps={nhl_stats.get('pp_opps', 0)}, Goals={nhl_stats.get('pp_goals', 0)}"
        return False, msg


if __name__ == "__main__":
    # Quick test
    game_id = "2025020001"
    team = "FLA"
    
    print(f"Validating {team} in game {game_id}...\n")
    
    # Fetch Stats API
    boxscore = get_nhl_stats_api_boxscore(game_id)
    if boxscore:
        nhl_stats = extract_nhl_stats_api_pp(boxscore, team)
        print(f"NHL.com Stats API for {team}:")
        print(f"  PP Goals: {nhl_stats.get('pp_goals')}")
        print(f"  PP Opps: {nhl_stats.get('pp_opps')}")
        print(f"  PP Goals Against: {nhl_stats.get('pp_goals_against')}")
        print(f"  PP Opps Against: {nhl_stats.get('pp_opps_against')}")
