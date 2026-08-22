from pathlib import Path

import polars as pl
import pytest

from scripts.validate_third_down_features import (
    SeasonValidation,
    _validate_cross_season,
    validate_season,
)


def artifact() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2024, 2024],
            "home_third_down_known": [True, True],
            "away_third_down_known": [True, True],
            "third_down_off_epa_difference": [0.1, -0.1],
            "third_down_def_epa_difference": [0.2, -0.2],
            "third_down_conversion_difference": [0.05, -0.05],
            "third_down_stop_difference": [0.04, -0.04],
            "third_and_long_conversion_difference": [0.03, -0.03],
            "home_off_third_down_plays": [30, 40],
            "away_off_third_down_plays": [30, 40],
            "home_off_third_and_long_plays": [15, 20],
            "away_off_third_and_long_plays": [15, 20],
            "home_third_down_history_weeks": [6, 7],
            "away_third_down_history_weeks": [6, 7],
        }
    )


def test_validate_season_accepts_valid_artifact(tmp_path: Path) -> None:
    path = tmp_path / "third_down_features_2024.parquet"
    artifact().write_parquet(path)

    result = validate_season(path, 2024)

    assert result.rows == 2
    assert result.home_known == 1.0
    assert result.feature_coverage["third_down_off_epa_difference"] == 1.0


def test_validate_season_rejects_duplicate_game_id(tmp_path: Path) -> None:
    path = tmp_path / "third_down_features_2024.parquet"
    frame = artifact().with_columns(pl.lit("g1").alias("game_id"))
    frame.write_parquet(path)

    with pytest.raises(ValueError, match="duplicate"):
        validate_season(path, 2024)


def test_cross_season_validation_rejects_low_coverage() -> None:
    result = SeasonValidation(
        season=2024,
        rows=285,
        home_known=0.80,
        away_known=0.95,
        feature_coverage={
            "third_down_off_epa_difference": 0.95,
            "third_down_def_epa_difference": 0.95,
            "third_down_conversion_difference": 0.95,
            "third_down_stop_difference": 0.95,
            "third_and_long_conversion_difference": 0.95,
        },
        feature_mean={
            "third_down_off_epa_difference": 0.0,
            "third_down_def_epa_difference": 0.0,
            "third_down_conversion_difference": 0.0,
            "third_down_stop_difference": 0.0,
            "third_and_long_conversion_difference": 0.0,
        },
        feature_std={
            "third_down_off_epa_difference": 0.1,
            "third_down_def_epa_difference": 0.1,
            "third_down_conversion_difference": 0.1,
            "third_down_stop_difference": 0.1,
            "third_and_long_conversion_difference": 0.1,
        },
        sample_means={
            "home_off_third_down_plays": 40.0,
            "away_off_third_down_plays": 40.0,
            "home_off_third_and_long_plays": 20.0,
            "away_off_third_and_long_plays": 20.0,
            "home_third_down_history_weeks": 8.0,
            "away_third_down_history_weeks": 8.0,
        },
    )

    with pytest.raises(ValueError, match="below 90%"):
        _validate_cross_season([result])
