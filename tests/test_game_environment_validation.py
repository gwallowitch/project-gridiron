import polars as pl
import pytest

from gridiron.validation.game_environment_features import (
    validate_game_environment_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g"],
            "season": [2025],
            "week": [1],
            "home_team": ["BUF"],
            "away_team": ["MIA"],
            "temperature_f": [30.0],
            "wind_mph": [10.0],
            "weather_text": ["snow"],
            "roof_text": ["outdoors"],
            "surface_text": ["grass"],
            "stadium_text": ["Highmark"],
            "indoor_or_closed_roof": [False],
            "retractable_roof": [False],
            "rain_or_precipitation": [False],
            "snow_or_wintry": [True],
            "extreme_cold": [True],
            "extreme_heat": [False],
            "high_wind": [False],
            "environment_known": [True],
            "adverse_weather_count": [2],
            "adverse_weather": [True],
        }
    )


def test_validation_accepts_good_frame() -> None:
    validate_game_environment_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_game_environment_features(pl.concat([valid(), valid()]))


def test_negative_wind_fails() -> None:
    bad = valid().with_columns(pl.lit(-1.0).alias("wind_mph"))
    with pytest.raises(ValueError, match="negative"):
        validate_game_environment_features(bad)
