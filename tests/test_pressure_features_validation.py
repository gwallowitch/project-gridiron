from __future__ import annotations

import polars as pl
import pytest

from gridiron.validation.pressure_features import validate_pressure_features


def valid_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_pressure_known": [True],
            "away_pressure_known": [True],
            "home_pressure_history_weeks": [1],
            "away_pressure_history_weeks": [1],
            "pass_protection_advantage": [0.1],
            "pressure_creation_advantage": [0.1],
            "clean_dropback_advantage": [0.1],
            "pressured_off_epa_difference": [0.1],
            "pressured_def_epa_advantage": [0.1],
        }
    )


def test_valid_pressure_features_pass() -> None:
    validate_pressure_features(valid_frame())


def test_duplicate_games_fail_validation() -> None:
    frame = pl.concat([valid_frame(), valid_frame()])
    with pytest.raises(ValueError, match="duplicate game_id"):
        validate_pressure_features(frame)


def test_missing_columns_fail_validation() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        validate_pressure_features(valid_frame().drop("pass_protection_advantage"))
