"""Validation for weekly team-rating datasets."""

from __future__ import annotations

import polars as pl

from gridiron.validation.team_ratings import validate_team_ratings

REQUIRED_WEEKLY_TEAM_RATING_COLUMNS = frozenset(
    {
        "season",
        "week",
        "team",
        "games_played",
        "offense_rating",
        "defense_rating",
        "discipline_rating",
        "situational_rating",
        "overall_rating",
    }
)


def validate_weekly_team_ratings(frame: pl.DataFrame) -> None:
    """Validate cumulative ratings for every represented week."""
    missing = REQUIRED_WEEKLY_TEAM_RATING_COLUMNS.difference(
        frame.columns
    )
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            "Weekly team ratings are missing required columns: "
            f"{missing_text}"
        )

    if frame.height < 2:
        raise ValueError(
            "Weekly team-rating data must contain at least two rows."
        )

    if frame.select(
        pl.struct(["season", "week", "team"]).n_unique()
    ).item() != frame.height:
        raise ValueError(
            "Weekly team-rating data contains duplicate team-week rows."
        )

    if frame.filter(pl.col("week") < 1).height:
        raise ValueError("Weekly team-rating data contains an invalid week.")

    if frame.filter(pl.col("games_played") < 1).height:
        raise ValueError(
            "Weekly team-rating data contains invalid games played."
        )

    for week in sorted(frame["week"].unique().to_list()):
        weekly_slice = frame.filter(pl.col("week") == week).drop(
            "season",
            "week",
        )
        validate_team_ratings(weekly_slice)
