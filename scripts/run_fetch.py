"""Runner script for fetching and aggregating team stats."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator.assessment import TeamAssessment
from src.orchestrator.fetcher_and_aggregator import GameFetcherAndAggregator

# Paths
db_path = str(Path("Data") / "test_nhl_stats.db")
schedule_path = str(Path("Data") / "schedule.csv")

# Get team from command line
team = sys.argv[1] if len(sys.argv) > 1 else "FLA"

# Assess
assessor = TeamAssessment(db_path, schedule_path)
assessment = assessor.assess_team(team)
assessor.print_assessment(assessment)

# Fetch and store
if assessment['unfetched_count'] > 0:
    fetcher = GameFetcherAndAggregator(db_path, rate_limit_delay=2.0)
    schedule = assessor.load_schedule()
    fetcher.fetch_and_store_team(team, assessment['unfetched_game_ids'], schedule)
else:
    print("✅ All games already fetched!")
