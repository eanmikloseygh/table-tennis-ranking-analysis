#!/usr/bin/env python3
"""
Table-tennis rankings analysis
------------------------------
Input: monthly top-200 rankings CSV with columns:
date, rank, player, age, country, hand, grip, style, rating, delta, source_file

Usage:
    python analyze_rankings.py rankings.csv --output-dir analysis_output

Outputs are CSV files ready to import into Power BI. This script assumes the
source data has already been cleaned, as requested.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd


def month_number(dates):
    """Convert YYYY-MM strings/datetimes to a monotonically increasing month index."""
    p = pd.to_datetime(dates)
    return p.dt.year * 12 + p.dt.month


def main(input_csv: str, output_dir: str):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_csv)
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y-%m")
    df["month_index"] = month_number(df["date"])
    df = df.sort_values(["player", "date"]).reset_index(drop=True)

    # A. Player-month table: career curves and month-to-month changes.
    # Changes are calculated only when the same player has records in adjacent months.
    grouped = df.groupby("player", sort=False)
    df["previous_date"] = grouped["date"].shift(1)
    df["previous_rank"] = grouped["rank"].shift(1)
    df["previous_rating"] = grouped["rating"].shift(1)
    df["month_gap"] = df["month_index"] - grouped["month_index"].shift(1)
    adjacent = df["month_gap"].eq(1)
    df["rank_change"] = (df["rank"] - df["previous_rank"]).where(adjacent)
    # Positive rank_change means the numeric rank worsened; negative means improved.
    df["rating_change"] = (df["rating"] - df["previous_rating"]).where(adjacent)
    df["abs_rating_change"] = df["rating_change"].abs()
    df["abs_rank_change"] = df["rank_change"].abs()
    df["in_top20"] = df["rank"].le(20)
    df["in_top200"] = df["rank"].le(200)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df.to_csv(out / "player_monthly_history.csv", index=False)

    # B. Career summaries.
    career_rows = []
    for player, g in df.groupby("player", sort=False):
        g = g.sort_values("date")
        first, last = g.iloc[0], g.iloc[-1]
        best_rank = g["rank"].min()
        peak_rank_rows = g.loc[g["rank"].eq(best_rank)]
        peak_rank_row = peak_rank_rows.iloc[0]  # earliest occurrence of best rank
        best_rating = g["rating"].max()
        rating_rows = g.loc[g["rating"].notna()]
        peak_rating_row = rating_rows.loc[rating_rows["rating"].eq(best_rating)].iloc[0] if not rating_rows.empty else None
        first_top20 = g.loc[g["rank"].le(20)]
        # A valid observed entry requires the player to first appear outside the Top 20.
        if first["rank"] > 20 and not first_top20.empty:
            top20_entry_date = first_top20.iloc[0]["date"]
            months_to_top20 = int(
                (top20_entry_date.year - first["date"].year) * 12
                + top20_entry_date.month - first["date"].month
            )
        else:
            top20_entry_date = pd.NaT
            months_to_top20 = np.nan

        adj_changes = g.loc[g["month_gap"].eq(1), "rating_change"].dropna()
        rank_changes = g.loc[g["month_gap"].eq(1), "rank_change"].dropna()
        age_at_start = first["age"] if pd.notna(first["age"]) else np.nan
        career_rows.append({
            "player": player,
            "country_at_first_observation": first["country"],
            "first_observed_date": first["date"],
            "last_observed_date": last["date"],
            "observed_months": int(g["date"].nunique()),
            "observed_span_months": int(
                (last["date"].year - first["date"].year) * 12
                + last["date"].month - first["date"].month + 1
            ),
            "first_observed_rank": first["rank"],
            "last_observed_rank": last["rank"],
            "first_observed_rating": first["rating"],
            "last_observed_rating": last["rating"],
            "best_observed_rank": best_rank,
            "date_best_rank_first_achieved": peak_rank_row["date"],
            "age_at_best_rank": peak_rank_row["age"],
            "best_observed_rating": best_rating,
            "date_best_rating_first_achieved": peak_rating_row["date"] if peak_rating_row is not None else pd.NaT,
            "rank_at_peak_rating": peak_rating_row["rank"] if peak_rating_row is not None else np.nan,
            "first_top20_date_after_observed_start": top20_entry_date,
            "months_from_first_observation_to_top20": months_to_top20,
            "already_top20_at_first_observation": bool(first["rank"] <= 20),
            "rating_change_sd_adjacent_months": adj_changes.std(),
            "mean_abs_rating_change_adjacent_months": adj_changes.abs().mean(),
            "largest_rating_increase_adjacent_months": adj_changes.max() if len(adj_changes) else np.nan,
            "largest_rating_decrease_adjacent_months": adj_changes.min() if len(adj_changes) else np.nan,
            "rank_change_sd_adjacent_months": rank_changes.std(),
            "mean_abs_rank_change_adjacent_months": rank_changes.abs().mean(),
            "age_at_first_observation": age_at_start,
        })
    career = pd.DataFrame(career_rows)
    career.to_csv(out / "player_career_summary.csv", index=False)

    # C. Monthly competitive landscape. Measures are calculated for Top 20 and Top 200.
    monthly_rows = []
    dates = sorted(df["date"].unique())
    previous = None
    for date in dates:
        cur = df.loc[df["date"].eq(date)]
        top20 = cur.loc[cur["rank"].le(20)]
        top200 = cur.loc[cur["rank"].le(200)]
        row = {"date": pd.Timestamp(date), "year": pd.Timestamp(date).year,
               "month": pd.Timestamp(date).month}
        for label, sub in [("top20", top20), ("top200", top200)]:
            ratings = sub["rating"].dropna()
            row.update({
                f"{label}_rating_mean": ratings.mean(),
                f"{label}_rating_median": ratings.median(),
                f"{label}_rating_sd": ratings.std(),
                f"{label}_rating_iqr": ratings.quantile(.75) - ratings.quantile(.25),
                f"{label}_rating_min": ratings.min(),
                f"{label}_rating_max": ratings.max(),
                f"{label}_rating_range": ratings.max() - ratings.min(),
            })
        row["top20_rank1_minus_rank20_rating_gap"] = (
            top20.loc[top20["rank"].eq(1), "rating"].mean()
            - top20.loc[top20["rank"].eq(20), "rating"].mean()
        )
        current_names = set(top20["player"])
        if previous is not None:
            prev_names = set(previous.loc[previous["rank"].le(20), "player"])
            retained = len(current_names & prev_names)
            entered = len(current_names - prev_names)
            exited = len(prev_names - current_names)
            row.update({
                "top20_retained_from_previous_month": retained,
                "top20_new_entries_vs_previous_month": entered,
                "top20_exits_vs_previous_month": exited,
                "top20_monthly_turnover_pct": 100 * entered / 20,
            })
            common = cur[["player", "rank"]].merge(
                previous[["player", "rank"]], on="player", how="inner",
                suffixes=("_current", "_previous")
            )
            common_top20 = common[
                common["rank_current"].le(20) | common["rank_previous"].le(20)
            ]
            row["mean_abs_rank_change_players_in_or_near_top20"] = (
                (common_top20["rank_current"] - common_top20["rank_previous"]).abs().mean()
            )
        else:
            row.update({
                "top20_retained_from_previous_month": np.nan,
                "top20_new_entries_vs_previous_month": np.nan,
                "top20_exits_vs_previous_month": np.nan,
                "top20_monthly_turnover_pct": np.nan,
                "mean_abs_rank_change_players_in_or_near_top20": np.nan,
            })
        monthly_rows.append(row)
        previous = cur
    monthly = pd.DataFrame(monthly_rows)
    monthly.to_csv(out / "monthly_competition_metrics.csv", index=False)

    # D. Annual comparisons use the last available month of each year.
    # The comparison is against the same month in the previous year (e.g. Oct 2026 vs Oct 2025).
    annual_rows = []
    snapshot_dates = (
        df[["date"]].drop_duplicates().assign(year=lambda x: x["date"].dt.year,
                                              month=lambda x: x["date"].dt.month)
        .sort_values("date").groupby("year").tail(1).sort_values("date")["date"].tolist()
    )
    snapshot_by_ym = {(pd.Timestamp(d).year, pd.Timestamp(d).month): pd.Timestamp(d)
                      for d in df["date"].drop_duplicates()}
    for date in snapshot_dates:
        date = pd.Timestamp(date)
        current = df.loc[df["date"].eq(date)]
        top20 = set(current.loc[current["rank"].le(20), "player"])
        prev_date = snapshot_by_ym.get((date.year - 1, date.month))
        if prev_date is not None:
            prev = df.loc[df["date"].eq(prev_date)]
            prev_top20 = set(prev.loc[prev["rank"].le(20), "player"])
            retained = len(top20 & prev_top20)
            entered = len(top20 - prev_top20)
            exited = len(prev_top20 - top20)
            turnover_pct = 100 * entered / 20
        else:
            retained = entered = exited = turnover_pct = np.nan
        annual_rows.append({
            "year": date.year,
            "snapshot_date": date,
            "comparison_date_previous_year": prev_date if prev_date is not None else pd.NaT,
            "top20_retained_vs_same_month_previous_year": retained,
            "top20_new_entries_vs_same_month_previous_year": entered,
            "top20_exits_vs_same_month_previous_year": exited,
            "top20_annual_turnover_pct": turnover_pct,
            "top20_membership_retention_pct": 100 * retained / 20 if pd.notna(retained) else np.nan,
            "top20_mean_rating": current.loc[current["rank"].le(20), "rating"].mean(),
            "top20_rating_sd": current.loc[current["rank"].le(20), "rating"].std(),
            "top20_rating_iqr": (
                current.loc[current["rank"].le(20), "rating"].quantile(.75)
                - current.loc[current["rank"].le(20), "rating"].quantile(.25)
            ),
            "top20_rank1_minus_rank20_rating_gap": (
                current.loc[current["rank"].eq(1), "rating"].mean()
                - current.loc[current["rank"].eq(20), "rating"].mean()
            ),
        })
    pd.DataFrame(annual_rows).to_csv(out / "annual_top20_metrics.csv", index=False)

    # E. Age-group comparison: change from first observed month to month +24.
    # Uses only numeric ages and players with observations at both exact endpoints.
    age_rows = []
    for player, g in df.groupby("player", sort=False):
        g = g.sort_values("date")
        first = g.iloc[0]
        if pd.isna(first["age"]):
            continue
        target_index = int(first["month_index"] + 24)
        endpoint = g.loc[g["month_index"].eq(target_index)]
        if endpoint.empty:
            continue
        end = endpoint.iloc[0]
        age = float(first["age"])
        if age < 21:
            cohort = "Under 21"
        elif age < 30:
            cohort = "21-29"
        else:
            cohort = "30+"
        age_rows.append({
            "player": player, "age_at_first_observation": age, "age_group": cohort,
            "start_date": first["date"], "end_date_24_months_later": end["date"],
            "start_rank": first["rank"], "rank_after_24_months": end["rank"],
            "rank_improvement_24m": first["rank"] - end["rank"],
            "start_rating": first["rating"], "rating_after_24_months": end["rating"],
            "rating_change_24m": end["rating"] - first["rating"],
        })
    age_players = pd.DataFrame(age_rows)
    age_players.to_csv(out / "age_progression_24_months_by_player.csv", index=False)
    if not age_players.empty:
        age_summary = age_players.groupby("age_group").agg(
            players=("player", "nunique"),
            mean_rank_improvement_24m=("rank_improvement_24m", "mean"),
            median_rank_improvement_24m=("rank_improvement_24m", "median"),
            mean_rating_change_24m=("rating_change_24m", "mean"),
            median_rating_change_24m=("rating_change_24m", "median"),
        ).reset_index()
    else:
        age_summary = pd.DataFrame(columns=[
            "age_group", "players", "mean_rank_improvement_24m",
            "median_rank_improvement_24m", "mean_rating_change_24m",
            "median_rating_change_24m"
        ])
    age_summary.to_csv(out / "age_progression_24_months_summary.csv", index=False)

    print(f"Analysis complete. CSV outputs saved to: {out.resolve()}")
    for file in sorted(out.glob("*.csv")):
        print(f"  {file.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze monthly table-tennis rankings.")
    parser.add_argument(
        "input_csv",
        nargs="?",
        default="rankings.csv"
    )
    parser.add_argument("--output-dir", default="analysis_output",
                        help="Directory for output CSV files (default: analysis_output)")
    args = parser.parse_args()
    main(args.input_csv, args.output_dir)
