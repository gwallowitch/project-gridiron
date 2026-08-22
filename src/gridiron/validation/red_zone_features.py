"""Validation for red-zone feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_red_zone_known",
    "away_red_zone_known",
    "home_red_zone_history_weeks",
    "away_red_zone_history_weeks",
    "red_zone_off_epa_difference",
    "red_zone_def_epa_difference",
    "red_zone_success_difference",
    "red_zone_td_rate_difference",
}


def validate_red_zone_features(frame: pl.DataFrame) -> None:
    """Raise when a red-zone feature artifact is invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Red-zone features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Red-zone features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Red-zone features contain invalid week values."
        )
