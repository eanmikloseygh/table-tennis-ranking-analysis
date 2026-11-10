
from pathlib import Path
import pandas as pd

# CSV file in the same folder as this script
CSV_FILE = Path(__file__).parent / "rankings.csv"

df = pd.read_csv(CSV_FILE)

# Remove leading/trailing spaces from player names
df["player"] = df["player"].astype("string").str.strip()

# Exclude missing names
df = df.dropna(subset=["player"])
df = df[df["player"] != ""]

# Get unique player names
unique_players = sorted(df["player"].unique(), key=str.casefold)

print(f"Total ranking records: {len(df):,}")
print(f"Unique players: {len(unique_players):,}")

print("\nFirst 50 unique players:")
for player in unique_players[:50]:
    print(player)

# Save the complete list
output_file = CSV_FILE.parent / "unique_players.csv"

pd.DataFrame({"player": unique_players}).to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)

print(f"\nFull list saved to: {output_file}")

# Count how many monthly ranking snapshots each player appears in
appearances = (
    df.groupby("player")["date"]
    .nunique()
    .sort_values(ascending=False)
)

print("\nTop 20 players by number of ranking snapshots:")
print(appearances.head(20).to_string())
