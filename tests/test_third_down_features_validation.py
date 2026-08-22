import polars as pl
import pytest

from gridiron.validation.third_down_features import (
    validate_third_down_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_third_down_known": [True],
            "away_third_down_known": [True],
            "home_third_down_history_weeks": [1],
            "away_third_down_history_weeks": [1],
            "third_down_off_epa_difference": [0.1],
            "third_down_def_epa_difference": [0.2],
            "third_down_conversion_difference": [0.03],
            "third_down_stop_difference": [0.04],
            "third_and_long_conversion_difference": [0.05],
        }
    )


def test_valid_third_down_features_pass() -> None:
    validate_third_down_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_third_down_features(pl.concat([valid(), valid()]))
