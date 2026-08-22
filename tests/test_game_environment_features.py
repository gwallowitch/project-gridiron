import polars as pl

from gridiron.features.game_environment import build_game_environment_features


def test_builds_environment_flags_from_common_columns() -> None:
    schedule = pl.DataFrame(
        {
            "game_id": ["cold", "dome"],
            "season": [2025, 2025],
            "week": [10, 10],
            "home_team": ["BUF", "MIN"],
            "away_team": ["MIA", "DET"],
            "temp": [28, 72],
            "wind": [18, 0],
            "weather": ["Light snow", "Clear"],
            "roof": ["outdoors", "dome"],
            "surface": ["grass", "artificial"],
            "stadium": ["Highmark", "US Bank"],
        }
    )

    out = build_game_environment_features(schedule)
    cold = out.filter(pl.col("game_id") == "cold").row(0, named=True)
    dome = out.filter(pl.col("game_id") == "dome").row(0, named=True)

    assert cold["extreme_cold"] is True
    assert cold["high_wind"] is True
    assert cold["snow_or_wintry"] is True
    assert cold["adverse_weather"] is True
    assert cold["adverse_weather_count"] == 3

    assert dome["indoor_or_closed_roof"] is True
    assert dome["adverse_weather"] is False


def test_parses_numeric_weather_strings() -> None:
    schedule = pl.DataFrame(
        {
            "game_id": ["g"],
            "season": [2025],
            "week": [5],
            "home_team": ["CHI"],
            "away_team": ["GB"],
            "temperature": ["31 F"],
            "wind_speed": ["16 mph"],
        }
    )

    row = build_game_environment_features(schedule).row(0, named=True)

    assert row["temperature_f"] == 31.0
    assert row["wind_mph"] == 16.0
    assert row["extreme_cold"] is True
    assert row["high_wind"] is True


def test_missing_optional_weather_columns_is_allowed() -> None:
    schedule = pl.DataFrame(
        {
            "game_id": ["g"],
            "season": [2025],
            "week": [1],
            "home_team": ["DAL"],
            "away_team": ["NYG"],
        }
    )

    row = build_game_environment_features(schedule).row(0, named=True)

    assert row["environment_known"] is False
    assert row["temperature_f"] is None
    assert row["wind_mph"] is None
    assert row["adverse_weather"] is False
