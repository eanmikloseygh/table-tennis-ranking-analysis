import pandas as pd

df = pd.read_csv(
    r"C:\Users\leosp\PycharmProjects\TableTennisRankingProj\rankings.csv"
)

# 1. Convert dates to proper dates
df["date"] = pd.to_datetime(
    df["date"], format="%Y-%m", errors="coerce"
)

print("\n--- DATASET OVERVIEW ---")
print("Rows:", len(df))
print("Unique players:", df["player"].nunique())
print("Ranking months:", df["date"].nunique())
print("Date range:", df["date"].min(), "to", df["date"].max())

# 2. Check duplicate player-month records
print("\n--- DUPLICATES ---")
print("Duplicate rows:", df.duplicated().sum())
print(
    "Duplicate player-month pairs:",
    df.duplicated(["date", "player"]).sum()
)

# 3. Check how many records appear each month
print("\n--- ROWS PER MONTH ---")
print(df.groupby("date").size().describe())
print("\nMonths with fewer than 200 rows:")
print(df.groupby("date").size().loc[lambda x: x < 200])

# 4. Check ranking positions
print("\n--- RANK VALIDATION ---")
print("Minimum rank:", df["rank"].min())
print("Maximum rank:", df["rank"].max())

print("\nRank counts for first 10 positions:")
print(df["rank"].value_counts().sort_index().head(10))

print("\n--- PLAYER ATTRIBUTES ---")
for col in ["hand", "grip", "style"]:
    print(f"\n{col}:")
    print(df[col].value_counts(dropna=False))

# 5. Check ratings
print("\n--- RATINGS ---")
print(df["rating"].describe())
print("Missing ratings:", df["rating"].isna().sum())

print("\n--- SOURCE FILES ---")
print("Unique source files:", df["source_file"].nunique())
print(df["source_file"].str.extract(
    r"history\\(\d{4})\\([^\\]+)$"
).value_counts().head(20))

# 6. Check whether player names are consistently represented
print("\n--- PLAYER NAME CHECK ---")
print(
    df.groupby("player")["player"].size()
      .sort_values(ascending=False).head(15)
)