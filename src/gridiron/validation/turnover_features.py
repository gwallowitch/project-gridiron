"""Validation for turnover-regression feature artifacts."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id", "season", "week", "home_team", "away_team",
    "home_turnover_known", "away_turnover_known",
    "home_interceptions_thrown_pg", "away_interceptions_thrown_pg",
    "home_fumbles_lost_pg", "away_fumbles_lost_pg",
    "home_turnovers_committed_pg", "away_turnovers_committed_pg",
    "interception_rate_difference", "fumble_lost_rate_difference",
    "turnover_rate_difference",
}


def validate_turnover_features(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Turnover features are missing columns: " + ", ".join(sorted(missing))
        )
    if frame["game_id"].n_unique() != frame.height:
        raise ValueError("Turnover features contain duplicate game_id values")
    if frame.filter(pl.col("week") < 1).height:
        raise ValueError("Turnover features contain invalid week values")
