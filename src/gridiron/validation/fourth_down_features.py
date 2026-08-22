"""Validation for fourth-down feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id", "season", "week", "home_team", "away_team",
    "home_fourth_down_known", "away_fourth_down_known",
    "home_fourth_down_history_weeks", "away_fourth_down_history_weeks",
    "fourth_down_off_epa_difference", "fourth_down_def_epa_difference",
    "fourth_down_conversion_difference", "fourth_down_stop_difference",
    "fourth_short_conversion_difference",
}


def validate_fourth_down_features(frame: pl.DataFrame) -> None:
    """Raise when a fourth-down feature artifact is invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Fourth-down features are missing columns: "
            + ", ".join(sorted(missing))
        )
    if frame["game_id"].n_unique() != frame.height:
        raise ValueError("Fourth-down features contain duplicate game_id values.")
    if frame.filter(pl.col("week") < 1).height:
        raise ValueError("Fourth-down features contain invalid week values.")
