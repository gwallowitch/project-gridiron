import polars as pl
import pytest

from gridiron.validation.fourth_down_features import validate_fourth_down_features


def valid() -> pl.DataFrame:
    return pl.DataFrame({
        "game_id": ["g1"], "season": [2024], "week": [2],
        "home_team": ["AAA"], "away_team": ["BBB"],
        "home_fourth_down_known": [True],
        "away_fourth_down_known": [True],
        "home_fourth_down_history_weeks": [1],
        "away_fourth_down_history_weeks": [1],
        "fourth_down_off_epa_difference": [0.1],
        "fourth_down_def_epa_difference": [0.2],
        "fourth_down_conversion_difference": [0.03],
        "fourth_down_stop_difference": [0.04],
        "fourth_short_conversion_difference": [0.05],
    })


def test_valid_fourth_down_features_pass() -> None:
    validate_fourth_down_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_fourth_down_features(pl.concat([valid(), valid()]))


def test_missing_column_fails() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        validate_fourth_down_features(valid().drop("fourth_down_stop_difference"))
