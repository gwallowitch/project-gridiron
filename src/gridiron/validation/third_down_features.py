"""Validation for third-down feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_third_down_known",
    "away_third_down_known",
    "home_third_down_history_weeks",
    "away_third_down_history_weeks",
    "third_down_off_epa_difference",
    "third_down_def_epa_difference",
    "third_down_conversion_difference",
    "third_down_stop_difference",
    "third_and_long_conversion_difference",
}


def validate_third_down_features(frame: pl.DataFrame) -> None:
    """Raise when a third-down feature artifact is invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Third-down features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Third-down features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Third-down features contain invalid week values."
        )
