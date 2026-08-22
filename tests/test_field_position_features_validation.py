from __future__ import annotations

import polars as pl
import pytest

from gridiron.validation.field_position_features import (
    validate_field_position_features,
)


def valid_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_field_position_known": [True],
            "away_field_position_known": [True],
            "home_field_position_history_weeks": [1],
            "away_field_position_history_weeks": [1],
            "off_start_field_position_advantage": [5.0],
            "def_field_position_advantage": [3.0],
            "short_field_rate_difference": [0.05],
            "long_field_avoidance_advantage": [0.02],
            "hidden_yards_field_position_advantage": [8.0],
        }
    )


def test_valid_field_position_features_pass() -> None:
    validate_field_position_features(valid_frame())


def test_duplicate_games_fail_validation() -> None:
    frame = pl.concat([valid_frame(), valid_frame()])
    with pytest.raises(ValueError, match="duplicate game_id"):
        validate_field_position_features(frame)
