from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.rest import build_rest_features


def sample_schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g3", "g4"],
            "season": [2025, 2025, 2025, 2025],
            "week": [1, 1, 2, 3],
            "gameday": [
                "2025-09-04",
                "2025-09-07",
                "2025-09-11",
                "2025-09-21",
            ],
            "home_team": ["A", "C", "B", "A"],
            "away_team": ["B", "D", "A", "C"],
        }
    )


def test_week_one_defaults_to_seven_days() -> None:
    result = build_rest_features(sample_schedule())
    week_one = result.filter(pl.col("week") == 1)

    assert week_one["home_rest_days"].to_list() == [7, 7]
    assert week_one["away_rest_days"].to_list() == [7, 7]
    assert week_one["rest_advantage"].to_list() == [0, 0]


def test_short_week_is_calculated_from_dates() -> None:
    result = build_rest_features(sample_schedule())
    row = result.filter(pl.col("game_id") == "g3").row(0, named=True)

    assert row["home_rest_days"] == 7
    assert row["away_rest_days"] == 7
    assert row["rest_advantage"] == 0


def test_bye_week_creates_positive_rest_advantage() -> None:
    result = build_rest_features(sample_schedule())
    row = result.filter(pl.col("game_id") == "g4").row(0, named=True)

    assert row["home_rest_days"] == 10
    assert row["away_rest_days"] == 14
    assert row["rest_advantage"] == -4


def test_invalid_date_is_rejected() -> None:
    schedule = sample_schedule().with_columns(
        pl.when(pl.col("game_id") == "g1")
        .then(pl.lit("not-a-date"))
        .otherwise(pl.col("gameday"))
        .alias("gameday")
    )

    with pytest.raises(ValueError, match="invalid or missing"):
        build_rest_features(schedule)


def test_missing_columns_are_rejected() -> None:
    with pytest.raises(ValueError, match="away_team"):
        build_rest_features(sample_schedule().drop("away_team"))


def test_empty_schedule_is_rejected() -> None:
    with pytest.raises(ValueError, match="no games"):
        build_rest_features(sample_schedule().clear())
