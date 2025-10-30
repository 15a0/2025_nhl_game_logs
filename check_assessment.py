"""Check what the assessment says about unfetched games."""
from src.orchestrator.assessment import TeamAssessment

a = TeamAssessment('Data/test_nhl_stats.db', 'Data/schedule.csv')

teams = ['ANA', 'BOS', 'BUF', 'CAR', 'CBJ', 'CGY', 'CHI', 'COL', 'DAL', 'DET']

total_unfetched = 0
for team in teams:
    assessment = a.assess_team(team)
    unfetched = assessment['unfetched_count']
    total_unfetched += unfetched
    print(f"{team}: {unfetched} unfetched (total in schedule: {assessment['total_completed']})")

print(f"\nTotal unfetched (first 10 teams): {total_unfetched}")
