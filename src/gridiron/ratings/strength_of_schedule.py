"""Leak-free weekly strength-of-schedule calculations."""

from __future__ import annotations

import polars as pl

NEUTRAL_RATING = 100.0

_REQUIRED_FEATURE_COLUMNS = frozenset(
    {
        "season",
        "week",
        "game_id",
        "team",
        "opponent",
    }
)

_REQUIRED_RATING_COLUMNS = frozenset(
    {
        "season",
        "week",
        "team",
        "games_played",
        "overall_rating",
    }
)


def build_strength_of_schedule(
    feature_store: pl.DataFrame,
    weekly_ratings: pl.DataFrame,
) -> pl.DataFrame:
    """Build cumulative weekly schedule strength using prior-week ratings.

    For week N, every opponent already faced is valued using that opponent's
    rating from week N-1. Missing prior-week ratings and all Week 1 opponents
    receive the neutral baseline of 100.0.
    """
    _validate_inputs(feature_store, weekly_ratings)

    results: list[pl.DataFrame] = []
    weeks = sorted(weekly_ratings["week"].unique().to_list())

    for week in weeks:
        current_teams = weekly_ratings.filter(
            pl.col("week") == week
        ).select(
            "season",
            "team",
            "games_played",
        )

        opponent_history = feature_store.filter(
            pl.col("week") <= week
        ).select(
            "season",
            "game_id",
            "team",
            "opponent",
        )

        if week == 1:
            weekly_sos = current_teams.with_columns(
                pl.lit(NEUTRAL_RATING).alias(
                    "average_opponent_rating"
                )
            )
        else:
            prior_ratings = weekly_ratings.filter(
                pl.col("week") == week - 1
            ).select(
                "season",
                pl.col("team").alias("opponent"),
                pl.col("overall_rating").alias("opponent_rating"),
            )

            schedule_values = (
                opponent_history.join(
                    prior_ratings,
                    on=["season", "opponent"],
                    how="left",
                )
                .with_columns(
                    pl.col("opponent_rating")
                    .fill_null(NEUTRAL_RATING)
                    .alias("opponent_rating")
                )
                .group_by("season", "team")
                .agg(
                    pl.col("opponent_rating")
                    .mean()
                    .alias("average_opponent_rating")
                )
            )

            weekly_sos = current_teams.join(
                schedule_values,
                on=["season", "team"],
                how="left",
            ).with_columns(
                pl.col("average_opponent_rating")
                .fill_null(NEUTRAL_RATING)
                .alias("average_opponent_rating")
            )

        results.append(
            weekly_sos.with_columns(
                pl.lit(week).alias("week"),
                pl.col("average_opponent_rating").alias(
                    "strength_of_schedule_rating"
                ),
            ).select(
                "season",
                "week",
                "team",
                "games_played",
                "average_opponent_rating",
                "strength_of_schedule_rating",
            )
        )

    return pl.concat(results).sort(["week", "team"])


def _validate_inputs(
    feature_store: pl.DataFrame,
    weekly_ratings: pl.DataFrame,
) -> None:
    missing_features = _REQUIRED_FEATURE_COLUMNS.difference(
        feature_store.columns
    )
    if missing_features:
        missing_text = ", ".join(sorted(missing_features))
        raise ValueError(
            "Team-game features are missing required columns: "
            f"{missing_text}"
        )

    missing_ratings = _REQUIRED_RATING_COLUMNS.difference(
        weekly_ratings.columns
    )
    if missing_ratings:
        missing_text = ", ".join(sorted(missing_ratings))
        raise ValueError(
            "Weekly ratings are missing required columns: "
            f"{missing_text}"
        )

    if feature_store.height == 0:
        raise ValueError("Team-game features contain no rows.")

    if weekly_ratings.height == 0:
        raise ValueError("Weekly ratings contain no rows.")

    if weekly_ratings.filter(pl.col("week") < 1).height:
        raise ValueError("Weekly ratings contain an invalid week.")
