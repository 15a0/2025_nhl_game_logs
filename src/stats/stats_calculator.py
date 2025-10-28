"""
Advanced Stats Calculator

Calculates all 13 high-signal stats from NHL API boxscore and play-by-play data.

13 High-Signal Stats:
1. Net Pen/60 - Net penalty advantage per 60 min
2. Pen Drawn/60 - Penalties drawn per 60 min
3. Pen Taken/60 - Penalties taken per 60 min
4. CF% - Corsi For % (shot attempts)
5. SCF% - Scoring Chances For %
6. HDF% - High-Danger Shots For %
7. HDC% - High-Danger Chances For %
8. HDCO% - High-Danger Chances On (net) %
9. xGF - Expected Goals For
10. xGA - Expected Goals Against
11. PP% - Power Play %
12. PK% - Penalty Kill %
13. FOW% - Faceoff Win %

Refactored from: get_game_detail.py (v1.0 prototype)
"""

import logging
from typing import Dict, Optional, Any, Tuple

from src.utils import calculate_xg, is_high_danger

logger = logging.getLogger(__name__)


def calculate_game_stats(
    boxscore: Dict[str, Any],
    play_by_play: Dict[str, Any],
    config: Optional[Dict] = None
) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Calculate all 13 high-signal stats for both teams in a game.
    
    Args:
        boxscore: Boxscore JSON from NHL API
        play_by_play: Play-by-play JSON from NHL API
        config: Optional config dict with xG and zone parameters
    
    Returns:
        Dict with team abbreviations as keys, stats dict as values
        Example: {
            "NJD": {"team": "NJD", "game_id": "2025020001", "cf_pct": 52.3, ...},
            "COL": {"team": "COL", "game_id": "2025020001", "cf_pct": 47.7, ...}
        }
        Returns None if data is invalid or game is in future state
    """
    if not boxscore or not play_by_play:
        logger.error("Boxscore or play-by-play data is missing")
        return None
    
    # Check game state
    game_state = play_by_play.get('gameState')
    if game_state == "FUT":
        logger.warning("Game is in the future (FUT). No play-by-play data available yet.")
        return None
    
    # Extract team info from boxscore
    home_team = boxscore.get("homeTeam", {})
    away_team = boxscore.get("awayTeam", {})
    home_abbrev = home_team.get("abbrev", "")
    away_abbrev = away_team.get("abbrev", "")
    game_id = boxscore.get("id", "N/A")
    game_date = boxscore.get("gameDate", "N/A")
    
    if not home_abbrev or not away_abbrev:
        logger.error("Could not extract team abbreviations from boxscore")
        return None
    
    # Initialize stats dict for both teams
    stats = {
        home_abbrev: {
            "team": home_abbrev,
            "game_id": game_id,
            "date": game_date,
            "side": "home"
        },
        away_abbrev: {
            "team": away_abbrev,
            "game_id": game_id,
            "date": game_date,
            "side": "away"
        }
    }
    
    # Calculate Boxscore Stats (Tier 1)
    _calculate_boxscore_stats(stats, home_team, away_team, home_abbrev, away_abbrev)
    
    # Calculate Play-by-Play Stats (Tier 2-4)
    plays = play_by_play.get("plays", [])
    _calculate_play_by_play_stats(
        stats,
        plays,
        home_team,
        away_team,
        home_abbrev,
        away_abbrev,
        config
    )
    
    return stats


def _calculate_boxscore_stats(
    stats: Dict,
    home_team: Dict,
    away_team: Dict,
    home_abbrev: str,
    away_abbrev: str
) -> None:
    """Calculate Tier 1 stats from boxscore (PP%, PK%, FOW%)."""
    
    # Home team boxscore stats
    stats[home_abbrev].update({
        "pp_pct": (home_team.get("powerPlayGoals", 0) / max(home_team.get("powerPlayOpportunities", 1), 1)) * 100,
        "pk_pct": ((home_team.get("powerPlayOpportunitiesAgainst", 0) - home_team.get("powerPlayGoalsAgainst", 0)) / max(home_team.get("powerPlayOpportunitiesAgainst", 1), 1)) * 100,
        "fow_pct": home_team.get("faceoffWinningPct", 0) * 100
    })
    
    # Away team boxscore stats
    stats[away_abbrev].update({
        "pp_pct": (away_team.get("powerPlayGoals", 0) / max(away_team.get("powerPlayOpportunities", 1), 1)) * 100,
        "pk_pct": ((away_team.get("powerPlayOpportunitiesAgainst", 0) - away_team.get("powerPlayGoalsAgainst", 0)) / max(away_team.get("powerPlayOpportunitiesAgainst", 1), 1)) * 100,
        "fow_pct": away_team.get("faceoffWinningPct", 0) * 100
    })


def _calculate_play_by_play_stats(
    stats: Dict,
    plays: list,
    home_team: Dict,
    away_team: Dict,
    home_abbrev: str,
    away_abbrev: str,
    config: Optional[Dict] = None
) -> None:
    """Calculate Tier 2-4 stats from play-by-play (Corsi, xG, penalties, etc.)."""
    
    # Initialize counters for both teams
    for team_abbrev in [home_abbrev, away_abbrev]:
        stats[team_abbrev].update({
            "cf": 0, "ca": 0,
            "scf": 0, "sca": 0,
            "hdc": 0, "hdca": 0,
            "hdco": 0, "hdcoa": 0,
            "hdsf": 0, "hdsfa": 0,
            "xgf": 0.0, "xga": 0.0,
            "pen_taken": 0, "pen_drawn": 0
        })
    
    # Process each play
    for play in plays:
        details = play.get("details", {})
        x = details.get("xCoord", 0)
        y = details.get("yCoord", 0)
        event = play.get("typeDescKey", "")
        play_team_id = details.get("eventOwnerTeamId")
        
        # Determine which team made this play
        if play_team_id == home_team.get("id"):
            play_team_abbrev = home_abbrev
            opponent_abbrev = away_abbrev
        elif play_team_id == away_team.get("id"):
            play_team_abbrev = away_abbrev
            opponent_abbrev = home_abbrev
        else:
            continue  # Skip if team not found
        
        # Check if shot is in high-danger zone
        is_hd = is_high_danger(x, y, config)
        
        # Process shot events (Corsi, xG, high-danger)
        if event in ["shot-on-goal", "missed-shot", "blocked-shot", "goal"]:
            
            # Corsi (all shot attempts)
            stats[play_team_abbrev]["cf"] += 1
            stats[opponent_abbrev]["ca"] += 1
            
            # High-danger chances
            if is_hd:
                stats[play_team_abbrev]["hdc"] += 1
                stats[opponent_abbrev]["hdca"] += 1
            
            # Scoring chances and xG (shots that reached goalie)
            if event in ["shot-on-goal", "goal"]:
                shot_type = details.get("shotType", "Wrist")
                xg_val = calculate_xg(x, y, shot_type, config)
                
                stats[play_team_abbrev]["scf"] += 1
                stats[opponent_abbrev]["sca"] += 1
                stats[play_team_abbrev]["xgf"] += xg_val
                stats[opponent_abbrev]["xga"] += xg_val
                
                # High-danger shots on net
                if is_hd:
                    stats[play_team_abbrev]["hdco"] += 1
                    stats[opponent_abbrev]["hdcoa"] += 1
                    stats[play_team_abbrev]["hdsf"] += 1
                    stats[opponent_abbrev]["hdsfa"] += 1
        
        # Process penalty events
        if event == "penalty":
            stats[play_team_abbrev]["pen_taken"] += 1
            stats[opponent_abbrev]["pen_drawn"] += 1
    
    # Calculate percentages
    for team_abbrev in [home_abbrev, away_abbrev]:
        team_stats = stats[team_abbrev]
        
        # Corsi %
        total_corsi = team_stats["cf"] + team_stats["ca"]
        team_stats["cf_pct"] = round(
            team_stats["cf"] / total_corsi * 100 if total_corsi > 0 else 0,
            1
        )
        
        # Scoring Chances %
        total_scf = team_stats["scf"] + team_stats["sca"]
        team_stats["scf_pct"] = round(
            team_stats["scf"] / total_scf * 100 if total_scf > 0 else 0,
            1
        )
        
        # High-Danger Chances %
        total_hdc = team_stats["hdc"] + team_stats["hdca"]
        team_stats["hdc_pct"] = round(
            team_stats["hdc"] / total_hdc * 100 if total_hdc > 0 else 0,
            1
        )
        
        # High-Danger Chances On %
        total_hdco = team_stats["hdco"] + team_stats["hdcoa"]
        team_stats["hdco_pct"] = round(
            team_stats["hdco"] / total_hdco * 100 if total_hdco > 0 else 0,
            1
        )
        
        # High-Danger Shots %
        total_hdsf = team_stats["hdsf"] + team_stats["hdsfa"]
        team_stats["hdf_pct"] = round(
            team_stats["hdsf"] / total_hdsf * 100 if total_hdsf > 0 else 0,
            1
        )
        
        # Round xG values
        team_stats["xgf"] = round(team_stats["xgf"], 2)
        team_stats["xga"] = round(team_stats["xga"], 2)
        
        # Penalty stats (note: not normalized to 60 min yet, requires TOI from boxscore)
        team_stats["pen_taken_60"] = team_stats["pen_taken"]
        team_stats["pen_drawn_60"] = team_stats["pen_drawn"]
        team_stats["net_pen_60"] = team_stats["pen_taken"] - team_stats["pen_drawn"]
