
from pathlib import Path
import pandas as pd

# Project paths
PROJECT_DIR = Path(
    r"C:\Users\leosp\PycharmProjects\TableTennisRankingProj"
)

RAW_FILE = PROJECT_DIR / "rankings.csv"
OUTPUT_DIR = PROJECT_DIR / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load raw data
df = pd.read_csv(RAW_FILE)

# Standardize column names
df.columns = df.columns.str.strip().str.lower()

# Parse monthly dates
df["date"] = pd.to_datetime(
    df["date"],
    format="%Y-%m",
    errors="coerce"
)

# Standardize text fields without changing player-name identity
for col in ["player", "hand", "grip", "style"]:
    df[col] = df[col].astype("string").str.strip()

# Ensure numeric columns have numeric types
for col in ["rank", "rating"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Remove only exact duplicate records
before = len(df)
df = df.drop_duplicates()
exact_duplicates_removed = before - len(df)

# Flag invalid records instead of silently deleting them
invalid_dates = df["date"].isna().sum()
invalid_ranks = (
    df["rank"].isna() |
    (df["rank"] <= 0)
).sum()

# Check duplicate player-date combinations
duplicate_player_months = df.duplicated(
    subset=["date", "player"],
    keep=False
).sum()

# Monthly coverage
monthly_counts = (
    df.groupby("date")
    .size()
    .rename("row_count")
    .reset_index()
)

# Expected calendar months
expected_months = pd.date_range(
    df["date"].min(),
    df["date"].max(),
    freq="MS"
)

observed_months = pd.DatetimeIndex(
    df["date"].dropna().unique()
)

missing_months = expected_months.difference(
    observed_months
)

# Save outputs
df.to_csv(
    OUTPUT_DIR / "rankings_cleaned.csv",
    index=False
)

monthly_counts.to_csv(
    OUTPUT_DIR / "monthly_coverage.csv",
    index=False
)

quality_report = {
    "rows_after_exact_deduplication": len(df),
    "unique_players": df["player"].nunique(),
    "unique_months": df["date"].nunique(),
    "first_month": str(df["date"].min()),
    "last_month": str(df["date"].max()),
    "exact_duplicates_removed": exact_duplicates_removed,
    "invalid_dates": int(invalid_dates),
    "invalid_ranks": int(invalid_ranks),
    "duplicate_player_month_rows": int(
        duplicate_player_months
    ),
    "missing_calendar_months": len(missing_months),
    "missing_age": int(df["age"].isna().sum()),
    "missing_country": int(df["country"].isna().sum()),
    "missing_rating": int(df["rating"].isna().sum()),
}

print("\nDATA QUALITY REPORT")
for key, value in quality_report.items():
    print(f"{key}: {value}")

print("\nMonths with fewer than 200 rows:")
print(
    monthly_counts.loc[
        monthly_counts["row_count"] < 200
    ].to_string(index=False)
)

print("\nMissing calendar months:", missing_months.tolist())

print("\nCleaned dataset saved to:", OUTPUT_DIR)
