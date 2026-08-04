from __future__ import annotations

import polars as pl
import pytest

from gridiron.ratings.strength_of_schedule import (
    build_strength_of_schedule,
)


def sample_feature_store() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2025] * 6,
            "week": [1, 1, 2, 2, 3, 3],
            "game_id": ["g1", "g1", "g2", "g2", "g3", "g3"],
            "team": ["A", "B", "A", "C", "B", "C"],
            "opponent": ["B", "A", "C", "A", "C", "B"],
        }
    )


def sample_weekly_ratings() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2025] * 8,
            "week": [1, 1, 2, 2, 2, 3, 3, 3],
            "team": ["A", "B", "A", "B", "C", "A", "B", "C"],
            "games_played": [1, 1, 2, 1, 1, 2, 2, 2],
            "overall_rating": [
                110.0,
                90.0,
                108.0,
                95.0,
                97.0,
                106.0,
                98.0,
                96.0,
            ],
        }
    )


def test_week_one_uses_neutral_schedule_rating() -> None:
    result = build_strength_of_schedule(
        sample_feature_store(),
        sample_weekly_ratings(),
    )

    week_one = result.filter(pl.col("week") == 1)

    assert week_one["strength_of_schedule_rating"].to_list() == [
        100.0,
        100.0,
    ]


def test_week_two_uses_week_one_opponent_ratings() -> None:
    result = build_strength_of_schedule(
        sample_feature_store(),
        sample_weekly_ratings(),
    )

    team_a = result.filter(
        (pl.col("week") == 2) & (pl.col("team") == "A")
    ).row(0, named=True)

    assert team_a["games_played"] == 2
    assert team_a["average_opponent_rating"] == pytest.approx(95.0)
    assert team_a["strength_of_schedule_rating"] == pytest.approx(95.0)


def test_week_three_uses_only_week_two_ratings() -> None:
    ratings = sample_weekly_ratings().vstack(
        pl.DataFrame(
            {
                "season": [2025],
                "week": [4],
                "team": ["C"],
                "games_played": [3],
                "overall_rating": [500.0],
            }
        )
    )

    result = build_strength_of_schedule(sample_feature_store(), ratings)

    team_b_week_three = result.filter(
        (pl.col("week") == 3) & (pl.col("team") == "B")
    ).row(0, named=True)

    assert team_b_week_three["average_opponent_rating"] == pytest.approx(
        (108.0 + 97.0) / 2
    )


def test_missing_prior_rating_uses_neutral_baseline() -> None:
    result = build_strength_of_schedule(
        sample_feature_store(),
        sample_weekly_ratings(),
    )

    team_c_week_two = result.filter(
        (pl.col("week") == 2) & (pl.col("team") == "C")
    ).row(0, named=True)

    assert team_c_week_two["average_opponent_rating"] == pytest.approx(
        110.0
    )


def test_strength_of_schedule_rejects_missing_columns() -> None:
    incomplete = sample_feature_store().drop("opponent")

    with pytest.raises(
        ValueError,
        match="missing required columns: opponent",
    ):
        build_strength_of_schedule(incomplete, sample_weekly_ratings())
