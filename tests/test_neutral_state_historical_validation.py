from pathlib import Path

import polars as pl
import pytest

from scripts.validate_neutral_state_features import (
    SeasonValidation,
    _validate_cross_season,
    validate_season,
)


def artifact() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2024, 2024],
            "home_neutral_state_known": [True, True],
            "away_neutral_state_known": [True, True],
            "neutral_off_epa_difference": [0.10, -0.10],
            "neutral_def_epa_difference": [0.08, -0.08],
            "neutral_success_difference": [0.03, -0.03],
            "neutral_yards_per_play_difference": [0.50, -0.50],
            "neutral_explosive_rate_difference": [0.02, -0.02],
            "home_off_neutral_plays": [120, 140],
            "away_off_neutral_plays": [120, 140],
            "home_def_neutral_plays": [120, 140],
            "away_def_neutral_plays": [120, 140],
            "home_neutral_state_history_weeks": [6, 7],
            "away_neutral_state_history_weeks": [6, 7],
        }
    )


def test_validate_season_accepts_valid_artifact(tmp_path: Path) -> None:
    path = tmp_path / "neutral_state_features_2024.parquet"
    artifact().write_parquet(path)

    result = validate_season(path, 2024)

    assert result.rows == 2
    assert result.home_known == 1.0
    assert result.feature_coverage["neutral_off_epa_difference"] == 1.0


def test_validate_season_rejects_duplicate_game_id(tmp_path: Path) -> None:
    path = tmp_path / "neutral_state_features_2024.parquet"
    frame = artifact().with_columns(pl.lit("g1").alias("game_id"))
    frame.write_parquet(path)

    with pytest.raises(ValueError, match="duplicate"):
        validate_season(path, 2024)


def test_cross_season_validation_rejects_low_known_coverage() -> None:
    result = SeasonValidation(
        season=2024,
        rows=285,
        home_known=0.80,
        away_known=0.95,
        feature_coverage={
            "neutral_off_epa_difference": 0.95,
            "neutral_def_epa_difference": 0.95,
            "neutral_success_difference": 0.95,
            "neutral_yards_per_play_difference": 0.95,
            "neutral_explosive_rate_difference": 0.95,
        },
        feature_mean={
            "neutral_off_epa_difference": 0.0,
            "neutral_def_epa_difference": 0.0,
            "neutral_success_difference": 0.0,
            "neutral_yards_per_play_difference": 0.0,
            "neutral_explosive_rate_difference": 0.0,
        },
        feature_std={
            "neutral_off_epa_difference": 0.1,
            "neutral_def_epa_difference": 0.1,
            "neutral_success_difference": 0.1,
            "neutral_yards_per_play_difference": 0.1,
            "neutral_explosive_rate_difference": 0.1,
        },
        sample_means={
            "home_off_neutral_plays": 120.0,
            "away_off_neutral_plays": 120.0,
            "home_def_neutral_plays": 120.0,
            "away_def_neutral_plays": 120.0,
            "home_neutral_state_history_weeks": 8.0,
            "away_neutral_state_history_weeks": 8.0,
        },
    )

    with pytest.raises(ValueError, match="below 90%"):
        _validate_cross_season([result])


def test_cross_season_validation_rejects_shallow_play_depth() -> None:
    result = SeasonValidation(
        season=2024,
        rows=285,
        home_known=0.95,
        away_known=0.95,
        feature_coverage={
            "neutral_off_epa_difference": 0.95,
            "neutral_def_epa_difference": 0.95,
            "neutral_success_difference": 0.95,
            "neutral_yards_per_play_difference": 0.95,
            "neutral_explosive_rate_difference": 0.95,
        },
        feature_mean={
            "neutral_off_epa_difference": 0.0,
            "neutral_def_epa_difference": 0.0,
            "neutral_success_difference": 0.0,
            "neutral_yards_per_play_difference": 0.0,
            "neutral_explosive_rate_difference": 0.0,
        },
        feature_std={
            "neutral_off_epa_difference": 0.1,
            "neutral_def_epa_difference": 0.1,
            "neutral_success_difference": 0.1,
            "neutral_yards_per_play_difference": 0.1,
            "neutral_explosive_rate_difference": 0.1,
        },
        sample_means={
            "home_off_neutral_plays": 30.0,
            "away_off_neutral_plays": 30.0,
            "home_def_neutral_plays": 30.0,
            "away_def_neutral_plays": 30.0,
            "home_neutral_state_history_weeks": 8.0,
            "away_neutral_state_history_weeks": 8.0,
        },
    )

    with pytest.raises(ValueError, match="offensive sample depth"):
        _validate_cross_season([result])
