import polars as pl
import pytest

from gridiron.validation.rushing_features import validate_rushing_features


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_rushing_known": [True],
            "away_rushing_known": [True],
            "home_rushing_history_weeks": [1],
            "away_rushing_history_weeks": [1],
            "rush_off_epa_difference": [0.1],
            "rush_def_epa_difference": [0.2],
            "rush_success_difference": [0.03],
            "explosive_run_rate_difference": [0.04],
        }
    )


def test_valid_rushing_features_pass() -> None:
    validate_rushing_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_rushing_features(pl.concat([valid(), valid()]))
