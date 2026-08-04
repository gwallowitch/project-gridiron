"""Weekly cumulative team metrics."""

from __future__ import annotations

import polars as pl

from gridiron.ratings.metrics import build_team_metrics


def build_weekly_team_metrics(
    feature_store: pl.DataFrame,
) -> pl.DataFrame:
    """Build cumulative team metrics through each week."""

    weeks = sorted(feature_store["week"].unique().to_list())

    weekly_results: list[pl.DataFrame] = []

    for week in weeks:
        cumulative = feature_store.filter(
            pl.col("week") <= week
        )

        metrics = build_team_metrics(cumulative).with_columns(
            pl.lit(week).alias("week")
        )

        weekly_results.append(metrics)

    return pl.concat(weekly_results).sort(
        "week",
        "team",
    )