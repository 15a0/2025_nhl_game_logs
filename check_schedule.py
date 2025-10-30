"""Check schedule completeness."""
import pandas as pd

df = pd.read_csv('Data/schedule.csv')
print(f'Total games in schedule: {len(df)}')
print(f'\nColumns: {list(df.columns)}')
print(f'\nFirst few rows:')
print(df.head())

print(f'\nUnique game_ids: {df["game_id"].nunique()}')
print(f'\nGames by home_team:')
print(df.groupby('home_team').size().sort_index())
