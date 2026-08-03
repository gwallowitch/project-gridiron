"""Validation for team-game feature datasets."""

from __future__ import annotations

import polars as pl

REQUIRED_TEAM_GAME_FEATURE_COLUMNS = frozenset(
    {
        "game_id",
        "season",
        "week",
        "team",
        "opponent",
        "offensive_plays",
        "offensive_epa_per_play",
        "offensive_success_rate",
        "defensive_epa_allowed_per_play",
    }
)


def validate_team_game_features(frame: pl.DataFrame) -> None:
    """Validate a team-game feature dataset."""
    missing = REQUIRED_TEAM_GAME_FEATURE_COLUMNS.difference(frame.columns)

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Team-game features are missing columns: {missing_text}"
        )

    if frame.height == 0:
        raise ValueError("Team-game feature data contains no rows.")

    duplicates = (
        frame.group_by(["game_id", "team"])
        .len()
        .filter(pl.col("len") > 1)
    )

    if duplicates.height:
        raise ValueError(
            "Team-game feature data contains duplicate game/team rows."
        )

    invalid_teams = frame.filter(
        pl.col("team").is_null()
        | pl.col("opponent").is_null()
        | (pl.col("team") == pl.col("opponent"))
    )

    if invalid_teams.height:
        raise ValueError(
            "Team-game feature data contains invalid team assignments."
        )
