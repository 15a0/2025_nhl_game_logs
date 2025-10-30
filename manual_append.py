"""Manually append staging to prod."""
import sqlite3

db_path = "Data/test_nhl_stats.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check staging
    cursor.execute("SELECT COUNT(*) FROM team_game_stats_staging")
    staging_count = cursor.fetchone()[0]
    print(f"Rows in staging: {staging_count}")
    
    # Append to prod (ignore duplicates)
    cursor.execute("""
        INSERT OR IGNORE INTO team_game_stats 
        (game_id, date, team, side, pp_goals, pp_opps, pp_goals_against, pp_opps_against,
         faceoff_wins, faceoff_losses, cf, ca, scf, sca, hdc, hdca, hdco, hdcoa, hdsf, hdsfa,
         xgf, xga, pen_taken, pen_drawn, toi_seconds)
        SELECT game_id, date, team, side, pp_goals, pp_opps, pp_goals_against, pp_opps_against,
               faceoff_wins, faceoff_losses, cf, ca, scf, sca, hdc, hdca, hdco, hdcoa, hdsf, hdsfa,
               xgf, xga, pen_taken, pen_drawn, toi_seconds
        FROM team_game_stats_staging
    """)
    conn.commit()
    
    # Check prod
    cursor.execute("SELECT COUNT(*) FROM team_game_stats")
    prod_count = cursor.fetchone()[0]
    print(f"Rows in prod: {prod_count}")
    
    # Clear staging
    cursor.execute("DELETE FROM team_game_stats_staging")
    conn.commit()
    print("✅ Appended staging to prod and cleared staging")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()

finally:
    conn.close()
