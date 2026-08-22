from pathlib import Path

import polars as pl
import pytest

from scripts.validate_field_position_features import (
    SeasonValidation,
    _validate_cross_season,
    validate_season,
)


def artifact() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2024, 2024],
            "home_field_position_known": [True, True],
            "away_field_position_known": [True, True],
            "off_start_field_position_advantage": [4.0, -4.0],
            "def_field_position_advantage": [3.0, -3.0],
            "short_field_rate_difference": [0.05, -0.05],
            "long_field_avoidance_advantage": [0.04, -0.04],
            "hidden_yards_field_position_advantage": [7.0, -7.0],
            "home_off_drives_started": [70, 80],
            "away_off_drives_started": [70, 80],
            "home_def_opponent_drives_started": [70, 80],
            "away_def_opponent_drives_started": [70, 80],
            "home_field_position_history_weeks": [6, 7],
            "away_field_position_history_weeks": [6, 7],
        }
    )


def test_validate_season_accepts_valid_artifact(tmp_path: Path) -> None:
    path = tmp_path / "field_position_features_2024.parquet"
    artifact().write_parquet(path)

    result = validate_season(path, 2024)

    assert result.rows == 2
    assert result.home_known == 1.0
    assert result.feature_coverage["off_start_field_position_advantage"] == 1.0


def test_validate_season_rejects_duplicate_game_id(tmp_path: Path) -> None:
    path = tmp_path / "field_position_features_2024.parquet"
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
            "off_start_field_position_advantage": 0.95,
            "def_field_position_advantage": 0.95,
            "short_field_rate_difference": 0.95,
            "long_field_avoidance_advantage": 0.95,
            "hidden_yards_field_position_advantage": 0.95,
        },
        feature_mean={
            "off_start_field_position_advantage": 0.0,
            "def_field_position_advantage": 0.0,
            "short_field_rate_difference": 0.0,
            "long_field_avoidance_advantage": 0.0,
            "hidden_yards_field_position_advantage": 0.0,
        },
        feature_std={
            "off_start_field_position_advantage": 1.0,
            "def_field_position_advantage": 1.0,
            "short_field_rate_difference": 0.1,
            "long_field_avoidance_advantage": 0.1,
            "hidden_yards_field_position_advantage": 1.0,
        },
        sample_means={
            "home_off_drives_started": 70.0,
            "away_off_drives_started": 70.0,
            "home_def_opponent_drives_started": 70.0,
            "away_def_opponent_drives_started": 70.0,
            "home_field_position_history_weeks": 8.0,
            "away_field_position_history_weeks": 8.0,
        },
    )

    with pytest.raises(ValueError, match="below 90%"):
        _validate_cross_season([result])


def test_cross_season_validation_rejects_shallow_drive_depth() -> None:
    result = SeasonValidation(
        season=2024,
        rows=285,
        home_known=0.95,
        away_known=0.95,
        feature_coverage={
            "off_start_field_position_advantage": 0.95,
            "def_field_position_advantage": 0.95,
            "short_field_rate_difference": 0.95,
            "long_field_avoidance_advantage": 0.95,
            "hidden_yards_field_position_advantage": 0.95,
        },
        feature_mean={
            "off_start_field_position_advantage": 0.0,
            "def_field_position_advantage": 0.0,
            "short_field_rate_difference": 0.0,
            "long_field_avoidance_advantage": 0.0,
            "hidden_yards_field_position_advantage": 0.0,
        },
        feature_std={
            "off_start_field_position_advantage": 1.0,
            "def_field_position_advantage": 1.0,
            "short_field_rate_difference": 0.1,
            "long_field_avoidance_advantage": 0.1,
            "hidden_yards_field_position_advantage": 1.0,
        },
        sample_means={
            "home_off_drives_started": 20.0,
            "away_off_drives_started": 20.0,
            "home_def_opponent_drives_started": 20.0,
            "away_def_opponent_drives_started": 20.0,
            "home_field_position_history_weeks": 8.0,
            "away_field_position_history_weeks": 8.0,
        },
    )

    with pytest.raises(ValueError, match="offensive drive-start sample depth"):
        _validate_cross_season([result])
