import polars as pl
import pytest

from gridiron.validation.drive_efficiency_features import (
    validate_drive_efficiency_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_drive_efficiency_known": [True],
            "away_drive_efficiency_known": [True],
            "home_drive_history_weeks": [1],
            "away_drive_history_weeks": [1],
            "drive_off_epa_difference": [0.1],
            "drive_def_epa_difference": [0.2],
            "scoring_drive_rate_difference": [0.03],
            "td_drive_rate_difference": [0.04],
            "plays_per_drive_difference": [0.5],
        }
    )


def test_valid_drive_efficiency_features_pass() -> None:
    validate_drive_efficiency_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_drive_efficiency_features(pl.concat([valid(), valid()]))
