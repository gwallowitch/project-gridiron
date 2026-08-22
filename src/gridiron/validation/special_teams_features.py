"""Validation for special-teams feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_special_teams_known",
    "away_special_teams_known",
    "home_special_teams_history_weeks",
    "away_special_teams_history_weeks",
    "fg_make_rate_difference",
    "punt_coverage_advantage",
    "punt_return_advantage",
    "punt_touchback_advantage",
}


def validate_special_teams_features(frame: pl.DataFrame) -> None:
    """Raise when a special-teams feature artifact is invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Special-teams features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Special-teams features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Special-teams features contain invalid week values."
        )
