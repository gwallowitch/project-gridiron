"""Validation for game-level injury features."""

from __future__ import annotations

import polars as pl

REQUIRED = frozenset(
    {
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
        "home_injury_score",
        "away_injury_score",
        "injury_score_difference",
        "home_affected_players",
        "away_affected_players",
        "home_out_players",
        "away_out_players",
        "home_injury_report_count",
        "away_injury_report_count",
        "home_injury_known",
        "away_injury_known",
        "kickoff_guard_applied",
        "source_timestamp_available",
    }
)


def validate_injury_features(frame: pl.DataFrame) -> None:
    """Raise when an injury feature artifact is invalid."""
    missing = REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Injury features are missing columns: "
            + ", ".join(sorted(missing))
        )
    if frame.height == 0:
        raise ValueError(
            "Injury feature dataset contains no games."
        )
    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Injury features contain duplicate game rows."
        )
    if any(frame.null_count().row(0)):
        raise ValueError(
            "Injury features contain null values."
        )

    invalid = frame.filter(
        pl.col("injury_score_difference")
        != (
            pl.col("home_injury_score")
            - pl.col("away_injury_score")
        )
    )
    if invalid.height:
        raise ValueError(
            "Injury score difference is inconsistent."
        )

    unsafe_unknown = frame.filter(
        (~pl.col("source_timestamp_available"))
        & (
            pl.col("home_injury_known")
            | pl.col("away_injury_known")
            | (pl.col("home_injury_score") != 0.0)
            | (pl.col("away_injury_score") != 0.0)
        )
    )
    if unsafe_unknown.height:
        raise ValueError(
            "Timestamp-unavailable injury data must remain neutral."
        )
