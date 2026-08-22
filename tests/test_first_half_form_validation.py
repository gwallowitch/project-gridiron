import polars as pl
import pytest

from gridiron.validation.first_half_form_features import (
    validate_first_half_form_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g"],
            "season": [2025],
            "week": [2],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_first_half_off_epa": [0.10],
            "away_first_half_off_epa": [0.05],
            "home_first_half_def_epa": [0.08],
            "away_first_half_def_epa": [0.02],
            "home_first_half_play_volume": [32.0],
            "away_first_half_play_volume": [30.0],
            "home_first_half_form_known": [True],
            "away_first_half_form_known": [True],
            "first_half_off_epa_advantage": [0.05],
            "first_half_def_epa_advantage": [0.06],
            "first_half_play_volume_advantage": [2.0],
        }
    )


def test_validation_accepts_valid_frame() -> None:
    validate_first_half_form_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_first_half_form_features(
            pl.concat([valid(), valid()])
        )
