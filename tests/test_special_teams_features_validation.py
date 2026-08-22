import polars as pl
import pytest

from gridiron.validation.special_teams_features import (
    validate_special_teams_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_special_teams_known": [True],
            "away_special_teams_known": [True],
            "home_special_teams_history_weeks": [1],
            "away_special_teams_history_weeks": [1],
            "fg_make_rate_difference": [0.1],
            "punt_coverage_advantage": [1.5],
            "punt_return_advantage": [2.5],
            "punt_touchback_advantage": [0.1],
        }
    )


def test_valid_special_teams_features_pass() -> None:
    validate_special_teams_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_special_teams_features(pl.concat([valid(), valid()]))
