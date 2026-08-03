"""Raw team metric aggregation for Project Gridiron."""

from __future__ import annotations

import polars as pl

REQUIRED_COLUMNS = frozenset(
    {
        "team",
        "offensive_plays",
        "offensive_yards",
        "offensive_epa",
        "offensive_success_rate",
        "explosive_play_rate",
        "turnovers",
        "defensive_epa_allowed_per_play",
        "defensive_success_rate_allowed",
        "defensive_explosive_play_rate_allowed",
        "takeaways",
    }
)


def build_team_metrics(feature_store: pl.DataFrame) -> pl.DataFrame:
    """Aggregate season-level metrics for each team."""
    missing = REQUIRED_COLUMNS.difference(feature_store.columns)

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Feature store is missing required columns: {missing_text}"
        )

    return (
        feature_store.group_by("team")
        .agg(
            pl.len().alias("games_played"),
            pl.col("offensive_plays").sum().alias("offensive_plays"),
            pl.col("offensive_yards").sum().alias("offensive_yards"),
            pl.col("offensive_epa").sum().alias("offensive_epa"),
            (
                (
                    pl.col("offensive_success_rate")
                    * pl.col("offensive_plays")
                ).sum()
                / pl.col("offensive_plays").sum()
            ).alias("offensive_success_rate"),
            (
                (
                    pl.col("explosive_play_rate")
                    * pl.col("offensive_plays")
                ).sum()
                / pl.col("offensive_plays").sum()
            ).alias("explosive_play_rate"),
            pl.col("turnovers").sum().alias("turnovers"),
            pl.col("takeaways").sum().alias("takeaways"),
            pl.col("defensive_epa_allowed_per_play")
            .mean()
            .alias("defensive_epa_allowed_per_play"),
            pl.col("defensive_success_rate_allowed")
            .mean()
            .alias("defensive_success_rate_allowed"),
            pl.col("defensive_explosive_play_rate_allowed")
            .mean()
            .alias("defensive_explosive_play_rate_allowed"),
        )
        .with_columns(
            (
                pl.col("offensive_epa")
                / pl.col("offensive_plays")
            ).alias("offensive_epa_per_play"),
            (
                pl.col("offensive_yards")
                / pl.col("offensive_plays")
            ).alias("offensive_yards_per_play"),
            (
                pl.col("takeaways")
                - pl.col("turnovers")
            ).alias("turnover_margin"),
        )
        .sort("team")
    )