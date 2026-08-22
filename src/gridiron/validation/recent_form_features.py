"""Validation for recent-form feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_recent_form_known",
    "away_recent_form_known",
    "home_recent_form_weeks",
    "away_recent_form_weeks",
    "recent_off_epa_difference",
    "recent_def_epa_advantage",
    "off_epa_trend_difference",
    "def_epa_trend_advantage",
    "off_success_trend_difference",
    "def_success_trend_advantage",
}


def validate_recent_form_features(frame: pl.DataFrame) -> None:
    """Raise when a recent-form artifact is invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Recent-form features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Recent-form features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Recent-form features contain invalid week values."
        )
