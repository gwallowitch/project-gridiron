"""Validation for team-rating datasets."""

from __future__ import annotations

import polars as pl

REQUIRED_TEAM_RATING_COLUMNS = frozenset(
    {
        "team",
        "games_played",
        "offense_rating",
        "defense_rating",
        "discipline_rating",
        "situational_rating",
        "overall_rating",
    }
)


def validate_team_ratings(frame: pl.DataFrame) -> None:
    """Validate one season of team ratings."""
    missing = REQUIRED_TEAM_RATING_COLUMNS.difference(frame.columns)

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Team ratings are missing required columns: {missing_text}"
        )

    if frame.height < 2:
        raise ValueError(
            "Team-rating data must contain at least two teams."
        )

    if frame["team"].null_count() > 0:
        raise ValueError("Team-rating data contains a null team.")

    if frame["team"].n_unique() != frame.height:
        raise ValueError(
            "Team-rating data contains duplicate team rows."
        )

    rating_columns = [
        "offense_rating",
        "defense_rating",
        "discipline_rating",
        "situational_rating",
        "overall_rating",
    ]

    null_ratings = (
        frame.select(
            [
                pl.col(column).null_count().alias(column)
                for column in rating_columns
            ]
        )
        .to_numpy()
        .sum()
    )

    if null_ratings > 0:
        raise ValueError("Team-rating data contains null ratings.")

    non_finite = frame.filter(
        pl.any_horizontal(
            [
                pl.col(column).is_infinite()
                | pl.col(column).is_nan()
                for column in rating_columns
            ]
        )
    )

    if non_finite.height:
        raise ValueError(
            "Team-rating data contains non-finite ratings."
        )