import polars as pl
import pytest

from gridiron.validation.passing_features import (
    validate_passing_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_passing_known": [True],
            "away_passing_known": [True],
            "home_passing_history_weeks": [1],
            "away_passing_history_weeks": [1],
            "pass_off_epa_difference": [0.1],
            "pass_def_epa_difference": [0.2],
            "pass_success_difference": [0.03],
            "off_sack_rate_advantage": [0.02],
            "def_sack_rate_advantage": [0.01],
            "explosive_pass_rate_difference": [0.04],
        }
    )


def test_valid_passing_features_pass() -> None:
    validate_passing_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_passing_features(
            pl.concat([valid(), valid()])
        )
