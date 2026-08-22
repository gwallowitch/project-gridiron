"""Validation for Step 83A pace / tempo features."""

from __future__ import annotations

import polars as pl

_REQUIRED = {
    "game_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "home_pregame_offensive_plays",
    "away_pregame_offensive_plays",
    "home_pregame_seconds_to_snap",
    "away_pregame_seconds_to_snap",
    "home_pregame_tempo_index",
    "away_pregame_tempo_index",
    "home_pace_tempo_known",
    "away_pace_tempo_known",
    "pace_play_volume_advantage",
    "pace_seconds_advantage",
    "tempo_index_advantage",
}


def validate_pace_tempo_features(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Pace/tempo features are missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError("Pace/tempo features contain duplicate game_id rows.")

    for column in (
        "home_pregame_offensive_plays",
        "away_pregame_offensive_plays",
    ):
        if frame.filter(pl.col(column) < 0).height:
            raise ValueError(f"{column} cannot be negative.")
