"""Validation for field-position feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_field_position_known",
    "away_field_position_known",
    "home_field_position_history_weeks",
    "away_field_position_history_weeks",
    "off_start_field_position_advantage",
    "def_field_position_advantage",
    "short_field_rate_difference",
    "long_field_avoidance_advantage",
    "hidden_yards_field_position_advantage",
}


def validate_field_position_features(frame: pl.DataFrame) -> None:
    """Raise when a field-position artifact is structurally invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Field-position features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Field-position features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Field-position features contain invalid week values."
        )
