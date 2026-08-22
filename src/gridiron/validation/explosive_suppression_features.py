"""Validation for explosive-play suppression feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_explosive_suppression_known",
    "away_explosive_suppression_known",
    "home_explosive_suppression_history_weeks",
    "away_explosive_suppression_history_weeks",
    "explosive_off_rate_difference",
    "explosive_suppression_advantage",
    "chunk_off_rate_difference",
    "chunk_suppression_advantage",
    "explosive_yards_share_difference",
}


def validate_explosive_suppression_features(
    frame: pl.DataFrame,
) -> None:
    """Raise when an explosive-suppression artifact is invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Explosive-suppression features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Explosive-suppression features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Explosive-suppression features contain invalid week values."
        )
