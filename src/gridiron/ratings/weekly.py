"""Build weekly cumulative team ratings."""

from __future__ import annotations

import polars as pl

from gridiron.ratings.team import build_team_ratings


def build_weekly_team_ratings(
    weekly_metrics: pl.DataFrame,
    *,
    season: int,
) -> pl.DataFrame:
    """Rate teams independently for each cumulative week."""
    if "week" not in weekly_metrics.columns:
        raise ValueError("Weekly metrics are missing required column: week")

    if weekly_metrics.height == 0:
        raise ValueError("Weekly metrics contain no rows.")

    weekly_results: list[pl.DataFrame] = []
    weeks = sorted(weekly_metrics["week"].unique().to_list())

    for week in weeks:
        metrics_for_week = weekly_metrics.filter(
            pl.col("week") == week
        )
        ratings = build_team_ratings(metrics_for_week).with_columns(
            pl.lit(season).alias("season"),
            pl.lit(week).alias("week"),
        )
        weekly_results.append(
            ratings.select(
                "season",
                "week",
                "team",
                "games_played",
                "offense_rating",
                "defense_rating",
                "discipline_rating",
                "situational_rating",
                "overall_rating",
            )
        )

    return pl.concat(weekly_results).sort(
        ["week", "overall_rating"],
        descending=[False, True],
    )
