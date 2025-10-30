"""Quick test of updated extraction logic."""

import sys
import requests
import json

# Add parent directory to path for imports
sys.path.insert(0, '/'.join(__file__.split('/')[:-2]))

from src.orchestrator.raw_extractor import extract_game_raw_stats

game_id = "2025020001"
boxscore_url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"
pbp_url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"

print(f"Fetching game {game_id}...\n")

# Fetch data
boxscore = requests.get(boxscore_url, timeout=10).json()
pbp = requests.get(pbp_url, timeout=10).json()

# Extract for FLA
print("=" * 70)
print("FLA EXTRACTION")
print("=" * 70)
fla_stats = extract_game_raw_stats(boxscore, pbp, game_id, "FLA")

if fla_stats:
    print(f"PP Goals: {fla_stats.get('pp_goals')}")
    print(f"PP Opps: {fla_stats.get('pp_opps')}")
    print(f"PP Goals Against: {fla_stats.get('pp_goals_against')}")
    print(f"PP Opps Against: {fla_stats.get('pp_opps_against')}")
    print(f"Faceoff Wins: {fla_stats.get('faceoff_wins')}")
    print(f"Faceoff Losses: {fla_stats.get('faceoff_losses')}")
    print(f"Corsi For: {fla_stats.get('cf')}")
    print(f"xGF: {fla_stats.get('xgf')}")
else:
    print("❌ Extraction failed")

# Extract for CHI
print("\n" + "=" * 70)
print("CHI EXTRACTION")
print("=" * 70)
chi_stats = extract_game_raw_stats(boxscore, pbp, game_id, "CHI")

if chi_stats:
    print(f"PP Goals: {chi_stats.get('pp_goals')}")
    print(f"PP Opps: {chi_stats.get('pp_opps')}")
    print(f"PP Goals Against: {chi_stats.get('pp_goals_against')}")
    print(f"PP Opps Against: {chi_stats.get('pp_opps_against')}")
    print(f"Faceoff Wins: {chi_stats.get('faceoff_wins')}")
    print(f"Faceoff Losses: {chi_stats.get('faceoff_losses')}")
    print(f"Corsi For: {chi_stats.get('cf')}")
    print(f"xGF: {chi_stats.get('xgf')}")
else:
    print("❌ Extraction failed")

# Sanity check: FLA and CHI should have opposite Corsi
print("\n" + "=" * 70)
print("SANITY CHECK")
print("=" * 70)
if fla_stats and chi_stats:
    fla_cf = fla_stats.get('cf', 0)
    chi_ca = chi_stats.get('ca', 0)
    print(f"FLA CF: {fla_cf}, CHI CA: {chi_ca} - Match: {fla_cf == chi_ca}")
    
    fla_ca = fla_stats.get('ca', 0)
    chi_cf = chi_stats.get('cf', 0)
    print(f"FLA CA: {fla_ca}, CHI CF: {chi_cf} - Match: {fla_ca == chi_cf}")
