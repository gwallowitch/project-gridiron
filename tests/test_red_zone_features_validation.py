import polars as pl
import pytest

from gridiron.validation.red_zone_features import validate_red_zone_features


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_red_zone_known": [True],
            "away_red_zone_known": [True],
            "home_red_zone_history_weeks": [1],
            "away_red_zone_history_weeks": [1],
            "red_zone_off_epa_difference": [0.1],
            "red_zone_def_epa_difference": [0.2],
            "red_zone_success_difference": [0.03],
            "red_zone_td_rate_difference": [0.04],
        }
    )


def test_valid_red_zone_features_pass() -> None:
    validate_red_zone_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_red_zone_features(
            pl.concat([valid(), valid()])
        )
