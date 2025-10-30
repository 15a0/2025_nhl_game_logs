"""
Smoke test: Multi-API fetcher for single team.

Collects game-level data from:
  - Stats API (statsapi.web.nhl.com): PP goals, PP opps, TOI
  - Web API PBP (api-web.nhle.com): Corsi, SCF, HDC, faceoffs, pens, xG

Clears team_game_stats and re-fetches for one team.
Outputs season totals for manual validation.

Usage:
  python smoke_test_multi_api_fetcher.py FLA
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestrator.assessment import TeamAssessment
from src.orchestrator.fetcher_and_aggregator import GameFetcherAndAggregator
import sqlite3

def clear_staging():
    """Clear staging table."""
    db_path = "Data/test_nhl_stats.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM team_game_stats_staging")
        conn.commit()
        print("✅ Cleared team_game_stats_staging")
    except Exception as e:
        print(f"❌ Error clearing table: {e}")
    finally:
        conn.close()

def print_season_totals(team: str, use_staging: bool = True):
    """Print season totals for manual validation."""
    db_path = "Data/test_nhl_stats.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    table_name = 'team_game_stats_staging' if use_staging else 'team_game_stats'
    
    try:
        cursor.execute(f"""
            SELECT 
                COUNT(*) as games,
                SUM(pp_goals) as pp_goals,
                SUM(pp_opps) as pp_opps,
                SUM(pp_goals_against) as pp_goals_against,
                SUM(pp_opps_against) as pp_opps_against,
                SUM(faceoff_wins) as faceoff_wins,
                SUM(faceoff_losses) as faceoff_losses,
                SUM(cf) as cf,
                SUM(ca) as ca,
                SUM(scf) as scf,
                SUM(sca) as sca,
                SUM(hdc) as hdc,
                SUM(hdca) as hdca,
                SUM(hdco) as hdco,
                SUM(hdcoa) as hdcoa,
                SUM(hdsf) as hdsf,
                SUM(hdsfa) as hdsfa,
                SUM(xgf) as xgf,
                SUM(xga) as xga,
                SUM(pen_taken) as pen_taken,
                SUM(pen_drawn) as pen_drawn
            FROM {table_name}
            WHERE team = ?
        """, (team,))
        
        row = cursor.fetchone()
        if row:
            totals = dict(row)
            
            print(f"\n{'='*70}")
            print(f"SEASON TOTALS FOR {team}")
            print(f"{'='*70}")
            print(f"Games:              {totals['games']}")
            print(f"\nPower Play:")
            print(f"  PP Goals:         {totals['pp_goals']}")
            print(f"  PP Opps:          {totals['pp_opps']}")
            if totals['pp_opps'] and totals['pp_opps'] > 0:
                pp_pct = (totals['pp_goals'] / totals['pp_opps']) * 100
                print(f"  PP%:              {pp_pct:.1f}%")
            print(f"  PP Goals Against: {totals['pp_goals_against']}")
            print(f"  PP Opps Against:  {totals['pp_opps_against']}")
            if totals['pp_opps_against'] and totals['pp_opps_against'] > 0:
                pk_pct = ((totals['pp_opps_against'] - totals['pp_goals_against']) / totals['pp_opps_against']) * 100
                print(f"  PK%:              {pk_pct:.1f}%")
            
            print(f"\nCorsi:")
            print(f"  CF:               {totals['cf']}")
            print(f"  CA:               {totals['ca']}")
            if (totals['cf'] + totals['ca']) > 0:
                cf_pct = (totals['cf'] / (totals['cf'] + totals['ca'])) * 100
                print(f"  CF%:              {cf_pct:.1f}%")
            
            print(f"\nScoring Chances:")
            print(f"  SCF:              {totals['scf']}")
            print(f"  SCA:              {totals['sca']}")
            if (totals['scf'] + totals['sca']) > 0:
                scf_pct = (totals['scf'] / (totals['scf'] + totals['sca'])) * 100
                print(f"  SCF%:             {scf_pct:.1f}%")
            
            print(f"\nHigh Danger Chances:")
            print(f"  HDC:              {totals['hdc']}")
            print(f"  HDCA:             {totals['hdca']}")
            print(f"  HDCO:             {totals['hdco']}")
            print(f"  HDCOA:            {totals['hdcoa']}")
            
            print(f"\nHigh Danger Shots:")
            print(f"  HDSF:             {totals['hdsf']}")
            print(f"  HDSFA:            {totals['hdsfa']}")
            
            print(f"\nExpected Goals:")
            print(f"  xGF:              {totals['xgf']:.2f}")
            print(f"  xGA:              {totals['xga']:.2f}")
            
            print(f"\nFaceoffs:")
            print(f"  Wins:             {totals['faceoff_wins']}")
            print(f"  Losses:           {totals['faceoff_losses']}")
            if (totals['faceoff_wins'] + totals['faceoff_losses']) > 0:
                fo_pct = (totals['faceoff_wins'] / (totals['faceoff_wins'] + totals['faceoff_losses'])) * 100
                print(f"  FO%:              {fo_pct:.1f}%")
            
            print(f"\nPenalties:")
            print(f"  Taken:            {totals['pen_taken']}")
            print(f"  Drawn:            {totals['pen_drawn']}")
            
            print(f"\n{'='*70}")
            print("👉 Compare these totals against NHL.com season stats for validation")
            print(f"{'='*70}\n")
        else:
            print(f"❌ No data found for {team}")
    
    except Exception as e:
        print(f"❌ Error querying totals: {e}")
    finally:
        conn.close()

def main():
    """Run smoke test."""
    if len(sys.argv) < 2:
        print("Usage: python smoke_test_multi_api_fetcher.py <TEAM>")
        print("Example: python smoke_test_multi_api_fetcher.py FLA")
        sys.exit(1)
    
    team = sys.argv[1].upper()
    db_path = "Data/test_nhl_stats.db"
    schedule_path = "Data/schedule.csv"
    
    print(f"\n{'='*70}")
    print(f"SMOKE TEST: Multi-API Fetcher for {team}")
    print(f"{'='*70}\n")
    
    # Clear staging
    clear_staging()
    
    # Assess team
    print(f"\n📋 Assessing {team}...")
    assessor = TeamAssessment(db_path, schedule_path)
    assessment = assessor.assess_team(team)
    assessor.print_assessment(assessment)
    
    # Fetch and store
    if assessment['unfetched_count'] > 0:
        print(f"\n🔄 Fetching {assessment['unfetched_count']} games for {team}...")
        fetcher = GameFetcherAndAggregator(db_path, rate_limit_delay=2.0)
        schedule = assessor.load_schedule()
        fetcher.fetch_and_store_team(team, assessment['unfetched_game_ids'], schedule)
    else:
        print(f"✅ All games already fetched!")
    
    # Print season totals
    print_season_totals(team)

if __name__ == "__main__":
    main()
