import polars as pl
import pytest

from gridiron.validation.play_consistency_features import (
    validate_play_consistency_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g"],
            "season": [2025],
            "week": [2],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_off_success_rate": [0.50],
            "away_off_success_rate": [0.45],
            "home_def_success_prevention_rate": [0.55],
            "away_def_success_prevention_rate": [0.52],
            "home_off_negative_play_rate": [0.10],
            "away_off_negative_play_rate": [0.12],
            "home_def_negative_play_forced_rate": [0.11],
            "away_def_negative_play_forced_rate": [0.09],
            "home_play_consistency_known": [True],
            "away_play_consistency_known": [True],
            "off_success_rate_advantage": [0.05],
            "def_success_prevention_advantage": [0.03],
            "success_rate_matchup_advantage": [0.08],
            "negative_play_matchup_advantage": [0.04],
        }
    )


def test_validation_accepts_valid_frame() -> None:
    validate_play_consistency_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_play_consistency_features(
            pl.concat([valid(), valid()])
        )


def test_rate_bounds_are_enforced() -> None:
    frame = valid().with_columns(
        pl.lit(1.2).alias("home_off_success_rate")
    )

    with pytest.raises(ValueError, match=r"outside \[0, 1\]"):
        validate_play_consistency_features(frame)
