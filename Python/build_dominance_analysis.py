

from pathlib import Path
import pandas as pd

# --------------------------------------------------
# 1. Paths and data loading
# --------------------------------------------------

PROJECT_DIR = Path(
    r"C:\Users\leosp\PycharmProjects\TableTennisRankingProj"
)

DATA_FILE = PROJECT_DIR / "data" / "processed" / "rankings_cleaned.csv"
OUTPUT_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_FILE, parse_dates=["date"])

# Standardize data types
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date", "player", "rank"]).copy()

# Normalize dates to the first day of each month
df["date"] = df["date"].dt.to_period("M").dt.to_timestamp()

for col in ["rank", "rating", "age"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Treat blank profile values as missing
profile_cols = ["country", "grip", "hand", "style"]

for col in profile_cols:
    df[col] = df[col].astype("string").str.strip()
    df[col] = df[col].replace("", pd.NA)

df = df.sort_values(["date", "rank"]).copy()

all_months = pd.date_range(
    df["date"].min(), df["date"].max(), freq="MS"
)

print(f"Loaded {len(df):,} ranking observations.")
print(f"Analyzing {len(all_months)} calendar months.")


# --------------------------------------------------
# 2. Player-level career metrics
# --------------------------------------------------

player_summary = (
    df.groupby("player")
    .agg(
        months_top_200=("date", "nunique"),
        months_top_20=("rank", lambda s: (s <= 20).sum()),
        months_top_10=("rank", lambda s: (s <= 10).sum()),
        months_ranked_1=("rank", lambda s: (s == 1).sum()),
        best_rank=("rank", "min"),
        average_rank=("rank", "mean"),
        peak_rating=("rating", "max"),
        average_rating=("rating", "mean"),
        first_observed_month=("date", "min"),
        last_observed_month=("date", "max"),
    )
    .reset_index()
)

player_summary["average_rank"] = (
    player_summary["average_rank"].round(2)
)
player_summary["average_rating"] = (
    player_summary["average_rating"].round(2)
)

player_summary["top_20_share_of_observed_months"] = (
    player_summary["months_top_20"]
    / player_summary["months_top_200"]
).round(4)


# --------------------------------------------------
# 3. Latest available player profile
# --------------------------------------------------

# Use the latest nonmissing value for each profile field.
# These are the latest recorded attributes, not necessarily
# the attributes the player had during their peak period.

profiles = (
    df.sort_values("date")
    .groupby("player")[profile_cols]
    .agg(
        lambda s: s.dropna().iloc[-1]
        if not s.dropna().empty
        else pd.NA
    )
    .reset_index()
)

# FIX: merge into player_summary, which is the DataFrame
# actually created above.
player_summary = player_summary.merge(
    profiles,
    on="player",
    how="left",
    validate="one_to_one",
)


# --------------------------------------------------
# 4. Longest consecutive run in the top 20
# --------------------------------------------------

# A month missing from a player's ranking record breaks
# their consecutive top-20 streak.

streak_rows = []

for player, player_df in df.groupby("player"):
    top20_months = set(
        player_df.loc[
            player_df["rank"] <= 20, "date"
        ]
    )

    current_streak = 0
    longest_streak = 0

    for month in all_months:
        if month in top20_months:
            current_streak += 1
            longest_streak = max(
                longest_streak, current_streak
            )
        else:
            current_streak = 0

    streak_rows.append({
        "player": player,
        "longest_consecutive_top20_months": longest_streak,
    })

streaks = pd.DataFrame(streak_rows)

player_summary = player_summary.merge(
    streaks,
    on="player",
    how="left",
    validate="one_to_one",
)


# --------------------------------------------------
# 5. Best rolling 36-month average rating
# --------------------------------------------------

# Each rolling window covers 36 calendar months.
# At least 30 nonmissing monthly ratings are required.
#
# Missing months are NOT filled with invented ratings.
# Each player's best window is selected by average rating.

rolling_results = []

for player, player_df in df.groupby("player"):
    monthly_rating = (
        player_df.drop_duplicates("date")
        .set_index("date")["rating"]
        .reindex(all_months)
    )

    rolling_mean = monthly_rating.rolling(
        window=36,
        min_periods=30,
    ).mean()

    if rolling_mean.notna().any():
        best_end_date = rolling_mean.idxmax()
        best_mean = rolling_mean.loc[best_end_date]

        window_start = (
            best_end_date - pd.DateOffset(months=35)
        )

        observed_count = monthly_rating.loc[
            window_start:best_end_date
        ].count()

        # Number of nonmissing monthly ratings, rather than
        # number of ranking rows, in the selected window.
        peak_average = round(float(best_mean), 2)
    else:
        best_end_date = pd.NaT
        window_start = pd.NaT
        observed_count = 0
        peak_average = None

    rolling_results.append({
        "player": player,
        "peak_36m_average_rating": peak_average,
        "peak_36m_window_start": window_start,
        "peak_36m_window_end": best_end_date,
        "ratings_observed_in_peak_window": int(observed_count),
    })

rolling_df = pd.DataFrame(rolling_results)

player_summary = player_summary.merge(
    rolling_df,
    on="player",
    how="left",
    validate="one_to_one",
)


# --------------------------------------------------
# 6. Prepare and export the player leaderboard
# --------------------------------------------------

# Give Power BI a clean, ready-to-use leaderboard table.
leaderboard_columns = [
    "player",
    "peak_36m_average_rating",
    "peak_36m_window_start",
    "peak_36m_window_end",
    "ratings_observed_in_peak_window",
    "best_rank",
    "peak_rating",
    "months_top_20",
    "months_top_200",
    "months_top_10",
    "months_ranked_1",
    "longest_consecutive_top20_months",
    "country",
    "grip",
    "hand",
    "style",
    "average_rank",
    "average_rating",
    "top_20_share_of_observed_months",
    "first_observed_month",
    "last_observed_month",
]

player_summary = player_summary[leaderboard_columns].copy()

player_summary = player_summary.sort_values(
    [
        "peak_36m_average_rating",
        "months_top_20",
    ],
    ascending=[False, False],
    na_position="last",
).reset_index(drop=True)

player_summary.insert(
    0,
    "leaderboard_rank",
    range(1, len(player_summary) + 1),
)

player_summary.to_csv(
    OUTPUT_DIR / "player_dominance.csv",
    index=False,
)


# --------------------------------------------------
# 7. Country share of top-20 placements
# --------------------------------------------------

top20 = df.loc[df["rank"] <= 20].copy()

country_overall = (
    top20.groupby("country", dropna=False)
    .agg(
        top20_placements=("player", "size"),
        unique_players=("player", "nunique"),
        months_represented=("date", "nunique"),
    )
    .reset_index()
)

total_placements = country_overall["top20_placements"].sum()

country_overall["share_of_top20_placements"] = (
    country_overall["top20_placements"]
    / total_placements
).round(4)

country_overall = country_overall.sort_values(
    "top20_placements",
    ascending=False,
)

country_overall.to_csv(
    OUTPUT_DIR / "country_top20_overall.csv",
    index=False,
)


# --------------------------------------------------
# 8. Monthly country shares of top-20 placements
# --------------------------------------------------

monthly_country = (
    top20.groupby(["date", "country"], dropna=False)
    .size()
    .rename("top20_placements")
    .reset_index()
)

monthly_totals = (
    monthly_country.groupby("date")["top20_placements"]
    .sum()
    .rename("total_top20_placements")
    .reset_index()
)

monthly_country = monthly_country.merge(
    monthly_totals,
    on="date",
    how="left",
)

monthly_country["share_of_top20_placements"] = (
    monthly_country["top20_placements"]
    / monthly_country["total_top20_placements"]
).round(4)

monthly_country.to_csv(
    OUTPUT_DIR / "country_top20_monthly.csv",
    index=False,
)


# --------------------------------------------------
# 9. Monthly turnover in the top 20
# --------------------------------------------------

top20_by_month = {
    month: set(group["player"])
    for month, group in top20.groupby("date")
}

turnover_rows = []
previous_players = None

for month in all_months:
    current_players = top20_by_month.get(month, set())

    if previous_players is None:
        entrants = None
        exits = None
        changed = None
    else:
        entrants = len(current_players - previous_players)
        exits = len(previous_players - current_players)

        changed = len(
            current_players.symmetric_difference(previous_players)
        ) // 2

    turnover_rows.append({
        "date": month,
        "top20_players": len(current_players),
        "new_entrants": entrants,
        "exits": exits,
        "players_replaced": changed,
    })

    previous_players = current_players

turnover_df = pd.DataFrame(turnover_rows)

turnover_df.to_csv(
    OUTPUT_DIR / "top20_turnover_monthly.csv",
    index=False,
)


# --------------------------------------------------
# 10. Print initial findings
# --------------------------------------------------

print("\n--- TOP PLAYERS BY PEAK 36-MONTH AVERAGE RATING ---")
print(
    player_summary.head(15)[
        [
            "leaderboard_rank",
            "player",
            "peak_36m_average_rating",
            "peak_36m_window_start",
            "peak_36m_window_end",
            "ratings_observed_in_peak_window",
            "best_rank",
            "average_rank",
            "peak_rating",
            "average_rating",
            "months_top_20",
            "country",
            "grip",
            "hand",
            "style",
        ]
    ].to_string(index=False)
)

print("\n--- MOST MONTHS IN THE TOP 20 ---")
print(
    player_summary.sort_values(
        ["months_top_20", "months_ranked_1"],
        ascending=False,
    ).head(15)[
        ["player", "months_top_20", "months_ranked_1", "best_rank"]
    ].to_string(index=False)
)

print("\n--- MOST MONTHS AT RANK 1 ---")
print(
    player_summary.sort_values(
        ["months_ranked_1", "months_top_20"],
        ascending=False,
    ).head(15)[
        ["player", "months_ranked_1", "months_top_20", "best_rank"]
    ].to_string(index=False)
)

print("\n--- HIGHEST PEAK RATINGS ---")
print(
    player_summary.sort_values(
        "peak_rating", ascending=False
    ).head(15)[
        ["player", "peak_rating", "best_rank", "months_ranked_1"]
    ].to_string(index=False)
)

print("\n--- LONGEST CONSECUTIVE TOP-20 STREAKS ---")
print(
    player_summary.sort_values(
        "longest_consecutive_top20_months",
        ascending=False,
    ).head(15)[
        ["player", "longest_consecutive_top20_months", "months_top_20"]
    ].to_string(index=False)
)

print("\n--- COUNTRIES BY TOP-20 SHARE ---")
print(country_overall.head(15).to_string(index=False))

print("\n--- MOST TOP-20 TURNOVER ---")
print(
    turnover_df.sort_values(
        "players_replaced", ascending=False
    ).head(10).to_string(index=False)
)

print("\nCreated analytical datasets:")

for filename in [
    "player_dominance.csv",
    "country_top20_overall.csv",
    "country_top20_monthly.csv",
    "top20_turnover_monthly.csv",
]:
    print(OUTPUT_DIR / filename)
