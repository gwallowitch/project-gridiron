from pathlib import Path

import polars as pl
import pytest

from scripts.validate_fourth_down_features import (
    SeasonValidation,
    _validate_cross_season,
    validate_season,
)


def artifact() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2024, 2024],
            "home_fourth_down_known": [True, True],
            "away_fourth_down_known": [True, True],
            "fourth_down_off_epa_difference": [0.10, -0.10],
            "fourth_down_def_epa_difference": [0.08, -0.08],
            "fourth_down_conversion_difference": [0.05, -0.05],
            "fourth_down_stop_difference": [0.04, -0.04],
            "fourth_short_conversion_difference": [0.12, -0.12],
            "home_off_fourth_down_attempts": [8, 10],
            "away_off_fourth_down_attempts": [8, 10],
            "home_def_fourth_down_attempts_faced": [8, 10],
            "away_def_fourth_down_attempts_faced": [8, 10],
            "home_off_fourth_short_attempts": [4, 5],
            "away_off_fourth_short_attempts": [4, 5],
            "home_fourth_down_history_weeks": [6, 7],
            "away_fourth_down_history_weeks": [6, 7],
        }
    )


def test_validate_season_accepts_valid_artifact(tmp_path: Path) -> None:
    path = tmp_path / "fourth_down_features_2024.parquet"
    artifact().write_parquet(path)

    result = validate_season(path, 2024)

    assert result.rows == 2
    assert result.home_known == 1.0
    assert result.feature_coverage["fourth_down_conversion_difference"] == 1.0


def test_validate_season_rejects_duplicate_game_id(tmp_path: Path) -> None:
    path = tmp_path / "fourth_down_features_2024.parquet"
    frame = artifact().with_columns(pl.lit("g1").alias("game_id"))
    frame.write_parquet(path)

    with pytest.raises(ValueError, match="duplicate"):
        validate_season(path, 2024)


def _result(
    *,
    home_known: float = 0.95,
    attempts: float = 8.0,
    short_coverage: float = 0.90,
) -> SeasonValidation:
    return SeasonValidation(
        season=2024,
        rows=285,
        home_known=home_known,
        away_known=0.95,
        feature_coverage={
            "fourth_down_off_epa_difference": 0.95,
            "fourth_down_def_epa_difference": 0.95,
            "fourth_down_conversion_difference": 0.95,
            "fourth_down_stop_difference": 0.95,
            "fourth_short_conversion_difference": short_coverage,
        },
        feature_mean={
            "fourth_down_off_epa_difference": 0.0,
            "fourth_down_def_epa_difference": 0.0,
            "fourth_down_conversion_difference": 0.0,
            "fourth_down_stop_difference": 0.0,
            "fourth_short_conversion_difference": 0.0,
        },
        feature_std={
            "fourth_down_off_epa_difference": 0.1,
            "fourth_down_def_epa_difference": 0.1,
            "fourth_down_conversion_difference": 0.1,
            "fourth_down_stop_difference": 0.1,
            "fourth_short_conversion_difference": 0.1,
        },
        sample_means={
            "home_off_fourth_down_attempts": attempts,
            "away_off_fourth_down_attempts": 8.0,
            "home_def_fourth_down_attempts_faced": 8.0,
            "away_def_fourth_down_attempts_faced": 8.0,
            "home_off_fourth_short_attempts": 4.0,
            "away_off_fourth_short_attempts": 4.0,
            "home_fourth_down_history_weeks": 8.0,
            "away_fourth_down_history_weeks": 8.0,
        },
    )


def test_cross_season_rejects_low_known_coverage() -> None:
    with pytest.raises(ValueError, match="below 90%"):
        _validate_cross_season([_result(home_known=0.80)])


def test_cross_season_rejects_low_attempt_depth() -> None:
    with pytest.raises(ValueError, match="sample depth"):
        _validate_cross_season([_result(attempts=2.0)])


def test_short_yardage_feature_uses_sparse_coverage_gate() -> None:
    _validate_cross_season([_result(short_coverage=0.75)])

    with pytest.raises(ValueError, match="below 70%"):
        _validate_cross_season([_result(short_coverage=0.60)])
