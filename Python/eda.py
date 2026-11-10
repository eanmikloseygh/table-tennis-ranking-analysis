
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

PROJECT_DIR = Path(
    r"C:\Users\leosp\PycharmProjects\TableTennisRankingProj"
)

DATA_FILE = PROJECT_DIR / "data" / "processed" / "rankings_cleaned.csv"
OUTPUT_DIR = PROJECT_DIR / "reports" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_FILE, parse_dates=["date"])

# 1. Dataset overview
print("\n--- DATASET OVERVIEW ---")
print(f"Rows: {len(df):,}")
print(f"Unique players: {df['player'].nunique():,}")
print(f"Countries represented: {df['country'].nunique():,}")
print(f"Date range: {df['date'].min():%Y-%m} to {df['date'].max():%Y-%m}")

# 2. Top 10 players by number of monthly appearances
print("\n--- MOST FREQUENTLY RANKED PLAYERS ---")
print(
    df["player"].value_counts().head(10).to_string()
)

# 3. Country representation across all observations
print("\n--- TOP 10 COUNTRIES BY OBSERVATIONS ---")
print(
    df["country"].value_counts().head(10).to_string()
)

# 4. Average age by year
df["year"] = df["date"].dt.year
print("\n--- AVERAGE AGE BY YEAR ---")
print(
    df.groupby("year")["age"].mean().round(2).to_string()
)

# 5. Average age of the top 10 players by year
top10 = df[df["rank"] <= 10]
print("\n--- TOP 10 AVERAGE AGE BY YEAR ---")
print(
    top10.groupby("year")["age"].mean().round(2).to_string()
)

# 6. Average age trend
avg_age = df.groupby("year")["age"].mean()

plt.figure(figsize=(10, 5))
avg_age.plot(marker="o")
plt.title("Average Age of Ranked Players Over Time")
plt.xlabel("Year")
plt.ylabel("Average Age")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "average_age_by_year.png", dpi=150)
plt.show()

print("\nEDA figures saved to:", OUTPUT_DIR)
