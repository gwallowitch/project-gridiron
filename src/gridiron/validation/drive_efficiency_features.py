"""Validation for drive-efficiency feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_drive_efficiency_known",
    "away_drive_efficiency_known",
    "home_drive_history_weeks",
    "away_drive_history_weeks",
    "drive_off_epa_difference",
    "drive_def_epa_difference",
    "scoring_drive_rate_difference",
    "td_drive_rate_difference",
    "plays_per_drive_difference",
}


def validate_drive_efficiency_features(frame: pl.DataFrame) -> None:
    """Raise when a drive-efficiency feature artifact is invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Drive-efficiency features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Drive-efficiency features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Drive-efficiency features contain invalid week values."
        )
