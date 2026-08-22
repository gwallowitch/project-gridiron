from __future__ import annotations

import polars as pl
import pytest

from gridiron.validation.neutral_state_features import (
    validate_neutral_state_features,
)


def valid_frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_neutral_state_known": [True],
            "away_neutral_state_known": [True],
            "home_neutral_state_history_weeks": [1],
            "away_neutral_state_history_weeks": [1],
            "neutral_off_epa_difference": [0.1],
            "neutral_def_epa_difference": [0.1],
            "neutral_success_difference": [0.02],
            "neutral_yards_per_play_difference": [0.4],
            "neutral_explosive_rate_difference": [0.03],
        }
    )


def test_valid_neutral_state_features_pass() -> None:
    validate_neutral_state_features(valid_frame())


def test_duplicate_games_fail_validation() -> None:
    frame = pl.concat([valid_frame(), valid_frame()])
    with pytest.raises(ValueError, match="duplicate game_id"):
        validate_neutral_state_features(frame)
