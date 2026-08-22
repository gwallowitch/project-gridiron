"""Validation for Step 84A performance stability features."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_mean_point_differential",
    "away_mean_point_differential",
    "home_point_differential_std",
    "away_point_differential_std",
    "home_mean_absolute_margin",
    "away_mean_absolute_margin",
    "home_close_game_rate",
    "away_close_game_rate",
    "home_performance_stability_known",
    "away_performance_stability_known",
    "stability_advantage",
    "recent_margin_advantage",
    "close_game_experience_advantage",
}


def validate_performance_stability_features(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Performance-stability features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Performance-stability features contain duplicate game_id rows."
        )

    for column in (
        "home_point_differential_std",
        "away_point_differential_std",
        "home_mean_absolute_margin",
        "away_mean_absolute_margin",
    ):
        if frame.filter(
            pl.col(column).is_not_null() & (pl.col(column) < 0.0)
        ).height:
            raise ValueError(f"{column} cannot be negative.")

    for column in ("home_close_game_rate", "away_close_game_rate"):
        if frame.filter(
            pl.col(column).is_not_null()
            & (
                (pl.col(column) < 0.0)
                | (pl.col(column) > 1.0)
            )
        ).height:
            raise ValueError(f"{column} must be between 0 and 1.")
