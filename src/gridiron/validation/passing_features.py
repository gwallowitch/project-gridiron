"""Validation for passing-efficiency artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_passing_known",
    "away_passing_known",
    "home_passing_history_weeks",
    "away_passing_history_weeks",
    "pass_off_epa_difference",
    "pass_def_epa_difference",
    "pass_success_difference",
    "off_sack_rate_advantage",
    "def_sack_rate_advantage",
    "explosive_pass_rate_difference",
}


def validate_passing_features(
    frame: pl.DataFrame,
) -> None:
    """Raise when a passing feature artifact is invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Passing features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Passing features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Passing features contain invalid week values."
        )
