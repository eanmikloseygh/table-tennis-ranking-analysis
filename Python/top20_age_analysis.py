
import pandas as pd
from pathlib import Path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "input_csv",
    nargs="?",
    default="rankings.csv"
)
parser.add_argument("--output-dir", default="analysis_output")
args = parser.parse_args()

out = Path(args.output_dir)
out.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(args.input_csv)

df["date"] = pd.to_datetime(df["date"], format="%Y-%m")
df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
df["age"] = pd.to_numeric(df["age"], errors="coerce")

df = df.sort_values(["date", "rank"])

# 1. Average age of the Top 20 for each month
top20 = df[df["rank"] <= 20].copy()

avg_age = (
    top20.groupby("date")
    .agg(
        average_top20_age=("age", "mean"),
        players_with_known_age=("age", "count"),
        top20_players=("player", "nunique")
    )
    .reset_index()
)

avg_age["year"] = avg_age["date"].dt.year
avg_age.to_csv(
    out / "top20_average_age_over_time.csv", index=False
)

# 2. Identify Top 20 entry and exit events
snapshots = {
    date: group.set_index("player")
    for date, group in df.groupby("date")
}

dates = sorted(snapshots)
events = []

for i in range(1, len(dates)):
    prev_date = dates[i - 1]
    curr_date = dates[i]

    prev = snapshots[prev_date]
    curr = snapshots[curr_date]

    prev_top20 = set(prev.index[prev["rank"] <= 20])
    curr_top20 = set(curr.index[curr["rank"] <= 20])

    # New Top 20 members
    for player in curr_top20 - prev_top20:
        events.append({
            "player": player,
            "event": "Entry",
            "event_date": curr_date,
            "age": curr.loc[player, "age"],
            "rank": curr.loc[player, "rank"]
        })

    # Players no longer in the Top 20
    for player in prev_top20 - curr_top20:
        events.append({
            "player": player,
            "event": "Exit",
            "event_date": curr_date,
            "age": prev.loc[player, "age"],
            "rank": prev.loc[player, "rank"]
        })

events_df = pd.DataFrame(
    events,
    columns=["player", "event", "event_date", "age", "rank"]
)

events_df["year"] = events_df["event_date"].dt.year

events_df.to_csv(
    out / "top20_entry_exit_age_events.csv", index=False
)

# 3. Monthly rank-versus-age scatter plot data
scatter = df[df["age"].notna() & df["rank"].notna()].copy()
scatter["player_month_id"] = (
    scatter["player"] + "|" + scatter["date"].dt.strftime("%Y-%m")
)

scatter.to_csv(
    out / "rank_vs_age_data.csv", index=False
)

print("Created:")
print("top20_average_age_over_time.csv")
print("top20_entry_exit_age_events.csv")
print("rank_vs_age_data.csv")
