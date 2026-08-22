"""Validation for explosive-play feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_explosive_pass_rate",
    "away_explosive_pass_rate",
    "home_explosive_rush_rate",
    "away_explosive_rush_rate",
    "home_explosive_play_rate",
    "away_explosive_play_rate",
    "home_explosive_play_known",
    "away_explosive_play_known",
    "explosive_pass_rate_advantage",
    "explosive_rush_rate_advantage",
    "explosive_play_rate_advantage",
}


def validate_explosive_play_features(
    frame: pl.DataFrame,
) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Explosive-play features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Explosive-play features contain duplicate game_id values."
        )

    rate_columns = [
        "home_explosive_pass_rate",
        "away_explosive_pass_rate",
        "home_explosive_rush_rate",
        "away_explosive_rush_rate",
        "home_explosive_play_rate",
        "away_explosive_play_rate",
    ]

    for column in rate_columns:
        invalid = frame.filter(
            pl.col(column).is_not_null()
            & (
                (pl.col(column) < 0.0)
                | (pl.col(column) > 1.0)
            )
        )
        if invalid.height:
            raise ValueError(
                f"{column} contains values outside [0, 1]."
            )
