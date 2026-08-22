"""Validation for turnover-stability feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_turnover_stability_known",
    "away_turnover_stability_known",
    "home_turnover_stability_history_weeks",
    "away_turnover_stability_history_weeks",
    "turnover_protection_advantage",
    "takeaway_creation_advantage",
    "interception_protection_advantage",
    "interception_creation_advantage",
    "off_fumble_luck_advantage",
    "def_fumble_luck_advantage",
    "combined_fumble_recovery_luck",
}


def validate_turnover_stability_features(
    frame: pl.DataFrame,
) -> None:
    """Raise when a turnover-stability artifact is invalid."""
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Turnover-stability features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Turnover-stability features contain duplicate game_id values."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError(
            "Turnover-stability features contain invalid week values."
        )
