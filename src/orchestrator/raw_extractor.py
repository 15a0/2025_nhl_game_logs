"""
Raw stat extraction from NHL API boxscore and play-by-play data.

Extracts: Corsi, xG, penalties, power plays, faceoffs.

PP stats are fetched from Stats API (statsapi.web.nhl.com) for accuracy.
Fallback to PBP derivation if Stats API unavailable.
"""

import math
import requests
from typing import Dict, Optional


def calculate_xg(x: float, y: float, shot_type: str) -> float:
    """
    Calculate expected goals (xG) for a shot.
    
    Simple model based on distance and shot type.
    
    Args:
        x: x-coordinate from play-by-play (-100 to 100)
        y: y-coordinate from play-by-play (-42.5 to 42.5)
        shot_type: Shot type (Wrist, Slap, Tip-in, etc.)
    
    Returns:
        Expected goals value (0.0 to 0.3)
    """
    # Distance to net (assume net at x=89 or -89, y=0)
    distance = math.sqrt((abs(x) - 89) ** 2 + y ** 2)
    
    # Basic weights: closer shots = higher xG
    if distance < 15:  # High-danger (slot)
        return 0.2 if shot_type != "Slap" else 0.15
    elif distance < 30:  # Mid-range
        return 0.1 if shot_type != "Slap" else 0.08
    else:  # Long-range
        return 0.05 if shot_type != "Slap" else 0.03


def get_pp_from_stats_api(game_id: str, team_abbrev: str) -> Optional[Dict]:
    """
    Fetch power play stats from Stats API (statsapi.web.nhl.com).
    
    This is the authoritative source for team-level PP stats (used by NHL.com).
    
    Args:
        game_id: Game ID (e.g., '2025020027')
        team_abbrev: Team abbreviation (e.g., 'FLA')
    
    Returns:
        Dict with pp_goals, pp_opps, pp_goals_against, pp_opps_against
        or None if fetch fails
    """
    try:
        url = f"https://statsapi.web.nhl.com/api/v1/game/{game_id}/boxscore"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        teams = data.get('teams', [])
        
        # Find our team
        for team_data in teams:
            team_info = team_data.get('team', {})
            if team_info.get('abbreviation') == team_abbrev:
                stats = team_data.get('teamStats', {}).get('teamSkaterStats', {})
                return {
                    'pp_goals': stats.get('powerPlayGoals', 0),
                    'pp_opps': stats.get('powerPlayOpportunities', 0),
                    'pp_goals_against': stats.get('powerPlayGoalsAgainst', 0),
                    'pp_opps_against': stats.get('powerPlayOpportunitiesAgainst', 0)
                }
        
        return None
    
    except Exception as e:
        # Silently fail; will fall back to PBP derivation
        return None


def extract_boxscore_raw(boxscore: Dict, team_abbrev: str) -> Dict:
    """
    Extract raw counts from boxscore.
    
    NOTE: PP goals and opps are extracted from play-by-play (boxscore is incomplete).
    This function returns empty dict for those fields; they're populated in extract_pbp_raw.
    
    Args:
        boxscore: Boxscore JSON from NHL API
        team_abbrev: Team abbreviation (e.g., 'FLA')
    
    Returns:
        Dict with raw counts (PP fields will be 0; populated from PBP)
    """
    # Find team in boxscore
    home_team = boxscore.get('homeTeam', {})
    away_team = boxscore.get('awayTeam', {})
    
    if home_team.get('abbrev') == team_abbrev:
        team_side = 'homeTeam'
    elif away_team.get('abbrev') == team_abbrev:
        team_side = 'awayTeam'
    else:
        return {}
    
    # NOTE: PP goals and opps are extracted from play-by-play, not boxscore
    # Boxscore player stats are incomplete (missing some PP goals)
    # Use play-by-play situationCode to detect PP situations
    
    return {
        'pp_goals': 0,  # Will be populated from PBP
        'pp_opps': 0,   # Will be populated from PBP
        'pp_goals_against': 0,  # Will be populated from PBP
        'pp_opps_against': 0,   # Will be populated from PBP
        'faceoff_wins': 0,      # Will be populated from PBP
        'faceoff_losses': 0     # Will be populated from PBP
    }


def extract_pbp_raw(play_by_play: Dict, boxscore: Dict, team_abbrev: str) -> Dict:
    """
    Extract raw counts from play-by-play data.
    
    Per Grok's guidance:
    - PP Opps: Count penalty events (typeCode == "MIN" only, exclude majors/misconducts)
    - Faceoffs: Count faceoff events, determine winner via eventOwnerTeamId
    - Corsi, xG, penalties: As before
    
    Args:
        play_by_play: Play-by-play JSON from NHL API
        boxscore: Boxscore JSON (for team IDs)
        team_abbrev: Team abbreviation (e.g., 'FLA')
    
    Returns:
        Dict with raw counts:
        {
            'cf': int,           # Corsi For
            'ca': int,           # Corsi Against
            'scf': int,          # Scoring Chances For
            'sca': int,          # Scoring Chances Against
            'hdc': int,          # High-Danger Chances For
            'hdca': int,         # High-Danger Chances Against
            'hdco': int,         # High-Danger Chances On (net)
            'hdcoa': int,        # High-Danger Chances On Against
            'hdsf': int,         # High-Danger Shots For
            'hdsfa': int,        # High-Danger Shots Against
            'xgf': float,        # Expected Goals For
            'xga': float,        # Expected Goals Against
            'pen_taken': int,    # Penalties Taken
            'pen_drawn': int,    # Penalties Drawn
            'pp_opps': int,      # Power Play Opportunities (for this team)
            'pp_opps_against': int,  # PP Opps Against (opponent's PP)
            'faceoff_wins': int, # Faceoffs Won
            'faceoff_losses': int  # Faceoffs Lost
        }
    """
    plays = play_by_play.get('plays', [])
    
    # Get team IDs from boxscore
    home_team = boxscore.get('homeTeam', {})
    away_team = boxscore.get('awayTeam', {})
    
    team_id = None
    if home_team.get('abbrev') == team_abbrev:
        team_id = home_team.get('id')
    elif away_team.get('abbrev') == team_abbrev:
        team_id = away_team.get('id')
    
    if not team_id:
        return {}
    
    # Initialize counters
    cf, ca = 0, 0
    scf, sca = 0, 0
    hdc, hdca = 0, 0
    hdco, hdcoa = 0, 0
    hdsf, hdsfa = 0, 0
    xgf, xga = 0.0, 0.0
    pen_taken, pen_drawn = 0, 0
    pp_goals, pp_goals_against = 0, 0
    pp_opps, pp_opps_against = 0, 0
    faceoff_wins, faceoff_losses = 0, 0
    
    # Process each play
    for play in plays:
        details = play.get('details', {})
        x = details.get('xCoord', 0)
        y = details.get('yCoord', 0)
        event = play.get('typeDescKey', '')
        play_team_id = details.get('eventOwnerTeamId')
        
        # Determine if this play is for or against our team
        is_for = play_team_id == team_id
        
        # Corsi (shots, missed shots, blocked shots, goals)
        if event in ['shot-on-goal', 'missed-shot', 'blocked-shot', 'goal']:
            is_high_danger = abs(abs(x) - 89) < 15 and abs(y) < 8.5
            
            # xG calculation for shots
            if event in ['shot-on-goal', 'goal']:
                shot_type = details.get('shotType', 'Wrist')
                xg_val = calculate_xg(x, y, shot_type)
                if is_for:
                    xgf += xg_val
                else:
                    xga += xg_val
            
            # Corsi count
            if is_for:
                cf += 1
                if is_high_danger:
                    hdc += 1
                    if event in ['shot-on-goal', 'goal']:
                        hdco += 1
                        hdsf += 1
                if event in ['shot-on-goal', 'goal']:
                    scf += 1
            else:
                ca += 1
                if is_high_danger:
                    hdca += 1
                    if event in ['shot-on-goal', 'goal']:
                        hdcoa += 1
                        hdsfa += 1
                if event in ['shot-on-goal', 'goal']:
                    sca += 1
        
        # Penalties (all types)
        if event == 'penalty':
            if is_for:
                pen_taken += 1
            else:
                pen_drawn += 1
            
            # Power play opportunities (only minor penalties create PP)
            # Per Grok: typeCode == "MIN" (exclude majors, misconducts, bench minors)
            # NOTE: committedByTeamId is often null, so we track via situationCode changes
            penalty_type_code = details.get('typeCode', '')
            if penalty_type_code == 'MIN':
                # Minor penalty: opponent gets PP opportunity
                if is_for:
                    # We took a penalty → opponent gets PP opportunity
                    pp_opps_against += 1
                else:
                    # Opponent took penalty → we get PP opportunity
                    pp_opps += 1
        
        # Power play goals (detect via situationCode, not strength field which is often null)
        # situationCode: 1451 = 5v4 PP, 1351 = 5v3 PP, 1341 = 5v3 (other), 1241 = 4v3
        # Note: Boxscore player stats are incomplete, so we count from PBP
        if event == 'goal':
            situation_code = play.get('situationCode', '')
            is_pp_goal = situation_code in ['1451', '1351', '1341', '1241']  # Various PP situations
            
            if is_pp_goal:
                if is_for:
                    pp_goals += 1
                else:
                    pp_goals_against += 1
        
        # Faceoffs (per Grok: use eventOwnerTeamId to determine winner)
        if event == 'faceoff':
            # eventOwnerTeamId indicates the team that won the faceoff
            if is_for:
                faceoff_wins += 1
            else:
                faceoff_losses += 1
    
    return {
        'cf': cf,
        'ca': ca,
        'scf': scf,
        'sca': sca,
        'hdc': hdc,
        'hdca': hdca,
        'hdco': hdco,
        'hdcoa': hdcoa,
        'hdsf': hdsf,
        'hdsfa': hdsfa,
        'xgf': round(xgf, 2),
        'xga': round(xga, 2),
        'pen_taken': pen_taken,
        'pen_drawn': pen_drawn,
        'pp_goals': pp_goals,
        'pp_goals_against': pp_goals_against,
        'pp_opps': pp_opps,
        'pp_opps_against': pp_opps_against,
        'faceoff_wins': faceoff_wins,
        'faceoff_losses': faceoff_losses
    }


def extract_game_raw_stats(boxscore: Dict, play_by_play: Dict, game_id: str, team_abbrev: str) -> Optional[Dict]:
    """
    Extract all raw stats for a team from a single game.
    
    Combines boxscore, play-by-play, and Stats API data.
    PP stats come from Stats API (authoritative source).
    Other stats come from PBP.
    
    Args:
        boxscore: Boxscore JSON from NHL API
        play_by_play: Play-by-play JSON from NHL API
        game_id: Game ID (e.g., '2025020027')
        team_abbrev: Team abbreviation (e.g., 'FLA')
    
    Returns:
        Dict with all raw stats, or None if extraction fails
    """
    if not boxscore or not play_by_play:
        return None
    
    # Extract from both sources
    boxscore_raw = extract_boxscore_raw(boxscore, team_abbrev)
    pbp_raw = extract_pbp_raw(play_by_play, boxscore, team_abbrev)
    
    if not boxscore_raw or not pbp_raw:
        return None
    
    # Combine
    combined = {**boxscore_raw, **pbp_raw}
    
    # Try to get PP stats from Stats API (authoritative source)
    pp_stats = get_pp_from_stats_api(game_id, team_abbrev)
    if pp_stats:
        # Override PP fields with Stats API data
        combined.update(pp_stats)
    
    return combined
