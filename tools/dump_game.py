"""Utility to dump game-level stats vertically for spot-checking."""

import sqlite3
import sys
from pathlib import Path

def dump_game(game_id: str):
    """Dump all stats for a game, team by team, stat by stat."""
    
    db_path = "Data/test_nhl_stats.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all stats for this game
    cursor.execute("""
        SELECT * FROM team_game_stats
        WHERE game_id = ?
        ORDER BY team
    """, (game_id,))
    
    rows = cursor.fetchall()
    
    if not rows:
        print(f"❌ No data found for game {game_id}")
        conn.close()
        return
    
    # Get column names (excluding id, game_id, date, created_at)
    all_columns = [description[0] for description in cursor.description]
    stat_columns = [col for col in all_columns 
                    if col not in ['id', 'game_id', 'date', 'created_at']]
    
    print("=" * 80)
    print(f"GAME {game_id} - RAW STATS")
    print("=" * 80)
    
    for row in rows:
        team = row['team']
        side = row['side']
        
        print(f"\n{team} ({side})")
        print("-" * 80)
        
        for col in stat_columns:
            value = row[col]
            # Format floats nicely
            if isinstance(value, float):
                value_str = f"{value:.2f}"
            else:
                value_str = str(value) if value is not None else "NULL"
            
            print(f"  {col:25s} : {value_str}")
    
    conn.close()
    
    # Also show the game info
    print("\n" + "=" * 80)
    print("GAME INFO")
    print("=" * 80)
    cursor = sqlite3.connect(db_path).cursor()
    cursor.execute("SELECT game_id, date FROM team_game_stats WHERE game_id = ? LIMIT 1", (game_id,))
    info = cursor.fetchone()
    if info:
        print(f"  Game ID: {info[0]}")
        print(f"  Date: {info[1]}")


if __name__ == "__main__":
    game_id = sys.argv[1] if len(sys.argv) > 1 else "2025020027"
    dump_game(game_id)
