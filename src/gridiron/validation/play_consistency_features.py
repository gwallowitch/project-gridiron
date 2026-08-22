"""Validation for Step 87A play-consistency features."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_off_success_rate",
    "away_off_success_rate",
    "home_def_success_prevention_rate",
    "away_def_success_prevention_rate",
    "home_off_negative_play_rate",
    "away_off_negative_play_rate",
    "home_def_negative_play_forced_rate",
    "away_def_negative_play_forced_rate",
    "home_play_consistency_known",
    "away_play_consistency_known",
    "off_success_rate_advantage",
    "def_success_prevention_advantage",
    "success_rate_matchup_advantage",
    "negative_play_matchup_advantage",
}


def validate_play_consistency_features(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Play-consistency features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            "Play-consistency features contain duplicate game_id rows."
        )

    rate_columns = (
        "home_off_success_rate",
        "away_off_success_rate",
        "home_def_success_prevention_rate",
        "away_def_success_prevention_rate",
        "home_off_negative_play_rate",
        "away_off_negative_play_rate",
        "home_def_negative_play_forced_rate",
        "away_def_negative_play_forced_rate",
    )

    for column in rate_columns:
        if frame.filter(
            pl.col(column).is_not_null()
            & (
                (pl.col(column) < 0.0)
                | (pl.col(column) > 1.0)
            )
        ).height:
            raise ValueError(
                f"{column} contains values outside [0, 1]."
            )
