import polars as pl
import pytest

from gridiron.validation.opponent_adjusted_features import (
    validate_opponent_adjusted_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [4],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_opponent_adjusted_known": [True],
            "away_opponent_adjusted_known": [True],
            "home_opponent_adjusted_history_weeks": [3],
            "away_opponent_adjusted_history_weeks": [3],
            "home_opponent_adjusted_opponents": [3],
            "away_opponent_adjusted_opponents": [3],
            "opponent_adjusted_off_epa_difference": [0.05],
            "opponent_adjusted_def_epa_difference": [0.04],
            "offensive_schedule_difficulty_advantage": [0.03],
            "defensive_schedule_difficulty_advantage": [0.02],
        }
    )


def test_valid_artifact_passes() -> None:
    validate_opponent_adjusted_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_opponent_adjusted_features(pl.concat([valid(), valid()]))


def test_missing_column_fails() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        validate_opponent_adjusted_features(
            valid().drop("opponent_adjusted_off_epa_difference")
        )
