import polars as pl
import pytest

from gridiron.validation.explosive_suppression_features import (
    validate_explosive_suppression_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_explosive_suppression_known": [True],
            "away_explosive_suppression_known": [True],
            "home_explosive_suppression_history_weeks": [1],
            "away_explosive_suppression_history_weeks": [1],
            "explosive_off_rate_difference": [0.01],
            "explosive_suppression_advantage": [0.02],
            "chunk_off_rate_difference": [0.03],
            "chunk_suppression_advantage": [0.04],
            "explosive_yards_share_difference": [0.05],
        }
    )


def test_valid_artifact_passes() -> None:
    validate_explosive_suppression_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_explosive_suppression_features(
            pl.concat([valid(), valid()])
        )


def test_missing_column_fails() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        validate_explosive_suppression_features(
            valid().drop("chunk_suppression_advantage")
        )
