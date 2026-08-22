import polars as pl
import pytest

from gridiron.validation.travel_fatigue_features import (
    validate_travel_fatigue_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2025],
            "week": [4],
            "home_team": ["MIA"],
            "away_team": ["SEA"],
            "travel_geography_known": [True],
            "away_travel_miles": [2720.0],
            "away_time_zone_shift_hours": [3],
            "eastward_time_zone_shift_hours": [3],
            "westward_time_zone_shift_hours": [0],
            "cross_country_travel": [True],
            "long_haul_travel": [True],
            "travel_rest_known": [True],
            "short_week_away": [False],
            "short_week_travel_miles": [0.0],
            "short_week_time_zone_shift": [0.0],
        }
    )


def test_valid_passes() -> None:
    validate_travel_fatigue_features(valid())


def test_duplicate_game_id_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_travel_fatigue_features(pl.concat([valid(), valid()]))


def test_negative_miles_fail() -> None:
    bad = valid().with_columns(pl.lit(-1.0).alias("away_travel_miles"))
    with pytest.raises(ValueError, match="negative"):
        validate_travel_fatigue_features(bad)
