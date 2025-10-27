import requests
import csv
import math

# Game ID for NJD vs. COL (10/26/2025, 4-3 OT win for NJD)
GAME_ID = "2025020001"
BOXSCORE_URL = f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/boxscore"
PLAY_BY_PLAY_URL = f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/play-by-play"

# Simple xG model: Assign xG based on shot distance
def calculate_xg(x, y, shot_type):
    # Distance to net (assume net at x=89 or -89, y=0)
    distance = math.sqrt((abs(x) - 89) ** 2 + y ** 2)
    # Basic weights: closer shots = higher xG
    if distance < 15:  # High-danger (slot)
        return 0.2 if shot_type != "Slap" else 0.15
    elif distance < 30:  # Mid-range
        return 0.1 if shot_type != "Slap" else 0.08
    else:  # Long-range
        return 0.05 if shot_type != "Slap" else 0.03

# Fetch boxscore
def fetch_boxscore():
    try:
        response = requests.get(BOXSCORE_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        print(f"Boxscore error: HTTP {response.status_code}")
        return None
    except Exception as e:
        print(f"Boxscore fetch failed: {e}")
        return None

# Fetch play-by-play
def fetch_play_by_play():
    try:
        response = requests.get(PLAY_BY_PLAY_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        print(f"Play-by-play error: HTTP {response.status_code}")
        return None
    except Exception as e:
        print(f"Play-by-play fetch failed: {e}")
        return None

# Compute team-level stats
def compute_team_stats(boxscore, play_by_play):
    if not boxscore or not play_by_play:
        return None

    # Plays are at top level, not under gameData
    plays = play_by_play.get("plays", [])
    
    # Teams are in boxscore, not play_by_play
    home_team = boxscore.get("homeTeam", {})
    away_team = boxscore.get("awayTeam", {})
    home_abbrev = home_team.get("abbrev", "")
    away_abbrev = away_team.get("abbrev", "")
    
    game_state = play_by_play.get('gameState')
    if game_state == "FUT":
        print("WARNING: Game is in the future (FUT). No play-by-play data available yet.")
        return None

    # Initialize stats for both teams
    stats = {
        home_abbrev: {"team": home_abbrev, "game_id": GAME_ID, "date": boxscore.get("gameDate", "N/A")},
        away_abbrev: {"team": away_abbrev, "game_id": GAME_ID, "date": boxscore.get("gameDate", "N/A")}
    }

    # Boxscore stats
    home = home_team
    away = away_team
    stats[home_abbrev].update({
        "pp_pct": (home.get("powerPlayGoals", 0) / max(home.get("powerPlayOpportunities", 1), 1)) * 100,
        "pk_pct": ((home.get("powerPlayOpportunitiesAgainst", 0) - home.get("powerPlayGoalsAgainst", 0)) / max(home.get("powerPlayOpportunitiesAgainst", 1), 1)) * 100,
        "fow_pct": home.get("faceoffWinningPct", 0) * 100
    })
    stats[away_abbrev].update({
        "pp_pct": (away.get("powerPlayGoals", 0) / max(away.get("powerPlayOpportunities", 1), 1)) * 100,
        "pk_pct": ((away.get("powerPlayOpportunitiesAgainst", 0) - away.get("powerPlayGoalsAgainst", 0)) / max(away.get("powerPlayOpportunitiesAgainst", 1), 1)) * 100,
        "fow_pct": away.get("faceoffWinningPct", 0) * 100
    })

    # Play-by-play stats
    for team in [home_abbrev, away_abbrev]:
        cf, ca = 0, 0
        scf, sca = 0, 0
        hdc, hdca = 0, 0
        hdco, hdcoa = 0, 0
        hdsf, hdsfa = 0, 0
        xgf = xga = 0
        pen_taken = pen_drawn = 0

        for play in plays:
            details = play.get("details", {})
            x = details.get("xCoord", 0)
            y = details.get("yCoord", 0)
            event = play.get("typeDescKey", "")
            play_team_id = details.get("eventOwnerTeamId")
            
            # Determine which team made this play
            if play_team_id == home_team.get("id"):
                play_team_abbrev = home_abbrev
            elif play_team_id == away_team.get("id"):
                play_team_abbrev = away_abbrev
            else:
                continue  # Skip if team not found
            
            is_for = play_team_abbrev == team

            # Corsi (shots, missed shots, blocked shots, goals)
            if event in ["shot-on-goal", "missed-shot", "blocked-shot", "goal"]:
                is_high_danger = abs(abs(x) - 89) < 15 and abs(y) < 8.5
                if event in ["shot-on-goal", "goal"]:
                    shot_type = details.get("shotType", "Wrist")
                    xg_val = calculate_xg(x, y, shot_type)
                    if is_for:
                        xgf += xg_val
                    else:
                        xga += xg_val

                if is_for:
                    cf += 1
                    if is_high_danger:
                        hdc += 1
                        if event in ["shot-on-goal", "goal"]:
                            hdco += 1
                            hdsf += 1
                    if event in ["shot-on-goal", "goal"]:
                        scf += 1
                else:
                    ca += 1
                    if is_high_danger:
                        hdca += 1
                        if event in ["shot-on-goal", "goal"]:
                            hdcoa += 1
                            hdsfa += 1
                    if event in ["shot-on-goal", "goal"]:
                        sca += 1

            # Penalties
            if event == "penalty":
                if is_for:
                    pen_taken += 1
                else:
                    pen_drawn += 1

        # Compute percentages
        total = cf + ca or 1
        stats[team].update({
            "cf_pct": round(cf / total * 100, 1),
            "scf_pct": round(scf / (scf + sca or 1) * 100, 1),
            "hdc_pct": round(hdc / (hdc + hdca or 1) * 100, 1),
            "hdco_pct": round(hdco / (hdco + hdcoa or 1) * 100, 1),
            "hdf_pct": round(hdsf / (hdsf + hdsfa or 1) * 100, 1),
            "xgf": round(xgf, 2),
            "xga": round(xga, 2),
            "pen_taken_60": round(pen_taken, 1),
            "pen_drawn_60": round(pen_drawn, 1),
            "net_pen_60": round(pen_taken - pen_drawn, 1)
        })

    return stats

# Export to CSV
def export_to_csv(stats, filename="game_stats_2025020476.csv"):
    if not stats:
        print("No stats to export.")
        return

    headers = [
        "game_id", "date", "team", "net_pen_60", "pen_drawn_60", "hdco_pct",
        "pen_taken_60", "hdc_pct", "cf_pct", "pp_pct", "hdf_pct", "fow_pct",
        "xgf", "scf_pct", "pk_pct", "xga"
    ]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter="|")
        writer.writeheader()
        for team in stats.values():
            writer.writerow(team)
    print(f"Exported {len(stats)} rows to {filename}")

# Main
if __name__ == "__main__":
    print("Fetching data...")
    boxscore = fetch_boxscore()
    play_by_play = fetch_play_by_play()
    print(f"Boxscore: {'OK' if boxscore else 'Failed'}")
    print(f"Play-by-play: {'OK' if play_by_play else 'Failed'}")
    team_stats = compute_team_stats(boxscore, play_by_play)
    export_to_csv(team_stats)