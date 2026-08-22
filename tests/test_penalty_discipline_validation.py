import polars as pl
import pytest

from gridiron.validation.penalty_discipline_features import (
    validate_penalty_discipline_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [4],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_penalty_discipline_known": [True],
            "away_penalty_discipline_known": [True],
            "home_discipline_history_weeks": [3],
            "away_discipline_history_weeks": [3],
            "penalty_yards_discipline_advantage": [1.0],
            "penalty_rate_discipline_advantage": [0.5],
            "offensive_penalty_discipline_advantage": [0.4],
            "defensive_penalty_discipline_advantage": [0.6],
        }
    )


def test_valid_artifact_passes() -> None:
    validate_penalty_discipline_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_penalty_discipline_features(
            pl.concat([valid(), valid()])
        )


def test_missing_column_fails() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        validate_penalty_discipline_features(
            valid().drop("penalty_rate_discipline_advantage")
        )
