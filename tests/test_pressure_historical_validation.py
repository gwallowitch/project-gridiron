from pathlib import Path

import polars as pl
import pytest

from scripts.validate_pressure_features import (
    SeasonValidation,
    _validate_cross_season,
    validate_season,
)


def artifact() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2024, 2024],
            "home_pressure_known": [True, True],
            "away_pressure_known": [True, True],
            "pass_protection_advantage": [0.02, -0.02],
            "pressure_creation_advantage": [0.03, -0.03],
            "clean_dropback_advantage": [0.02, -0.02],
            "pressured_off_epa_difference": [0.10, -0.10],
            "pressured_def_epa_advantage": [0.08, -0.08],
            "home_off_dropbacks": [100, 120],
            "away_off_dropbacks": [100, 120],
            "home_off_pressure_events": [20, 24],
            "away_off_pressure_events": [20, 24],
            "home_def_dropbacks_faced": [100, 120],
            "away_def_dropbacks_faced": [100, 120],
            "home_pressure_history_weeks": [6, 7],
            "away_pressure_history_weeks": [6, 7],
        }
    )


def test_validate_season_accepts_valid_artifact(tmp_path: Path) -> None:
    path = tmp_path / "pressure_features_2024.parquet"
    artifact().write_parquet(path)

    result = validate_season(path, 2024)

    assert result.rows == 2
    assert result.home_known == 1.0
    assert result.feature_coverage["pass_protection_advantage"] == 1.0


def test_validate_season_rejects_duplicate_game_id(tmp_path: Path) -> None:
    path = tmp_path / "pressure_features_2024.parquet"
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
            "pass_protection_advantage": 0.95,
            "pressure_creation_advantage": 0.95,
            "clean_dropback_advantage": 0.95,
            "pressured_off_epa_difference": 0.95,
            "pressured_def_epa_advantage": 0.95,
        },
        feature_mean={
            "pass_protection_advantage": 0.0,
            "pressure_creation_advantage": 0.0,
            "clean_dropback_advantage": 0.0,
            "pressured_off_epa_difference": 0.0,
            "pressured_def_epa_advantage": 0.0,
        },
        feature_std={
            "pass_protection_advantage": 0.1,
            "pressure_creation_advantage": 0.1,
            "clean_dropback_advantage": 0.1,
            "pressured_off_epa_difference": 0.1,
            "pressured_def_epa_advantage": 0.1,
        },
        sample_means={
            "home_off_dropbacks": 100.0,
            "away_off_dropbacks": 100.0,
            "home_off_pressure_events": 20.0,
            "away_off_pressure_events": 20.0,
            "home_def_dropbacks_faced": 100.0,
            "away_def_dropbacks_faced": 100.0,
            "home_pressure_history_weeks": 8.0,
            "away_pressure_history_weeks": 8.0,
        },
    )

    with pytest.raises(ValueError, match="below 90%"):
        _validate_cross_season([result])


def test_cross_season_validation_rejects_shallow_dropback_depth() -> None:
    result = SeasonValidation(
        season=2024,
        rows=285,
        home_known=0.95,
        away_known=0.95,
        feature_coverage={
            "pass_protection_advantage": 0.95,
            "pressure_creation_advantage": 0.95,
            "clean_dropback_advantage": 0.95,
            "pressured_off_epa_difference": 0.95,
            "pressured_def_epa_advantage": 0.95,
        },
        feature_mean={
            "pass_protection_advantage": 0.0,
            "pressure_creation_advantage": 0.0,
            "clean_dropback_advantage": 0.0,
            "pressured_off_epa_difference": 0.0,
            "pressured_def_epa_advantage": 0.0,
        },
        feature_std={
            "pass_protection_advantage": 0.1,
            "pressure_creation_advantage": 0.1,
            "clean_dropback_advantage": 0.1,
            "pressured_off_epa_difference": 0.1,
            "pressured_def_epa_advantage": 0.1,
        },
        sample_means={
            "home_off_dropbacks": 10.0,
            "away_off_dropbacks": 10.0,
            "home_off_pressure_events": 20.0,
            "away_off_pressure_events": 20.0,
            "home_def_dropbacks_faced": 10.0,
            "away_def_dropbacks_faced": 10.0,
            "home_pressure_history_weeks": 8.0,
            "away_pressure_history_weeks": 8.0,
        },
    )

    with pytest.raises(ValueError, match="dropback sample depth"):
        _validate_cross_season([result])
