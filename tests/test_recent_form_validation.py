import polars as pl
import pytest

from gridiron.validation.recent_form_features import (
    validate_recent_form_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [4],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_recent_form_known": [True],
            "away_recent_form_known": [True],
            "home_recent_form_weeks": [3],
            "away_recent_form_weeks": [3],
            "recent_off_epa_difference": [0.10],
            "recent_def_epa_advantage": [0.08],
            "off_epa_trend_difference": [0.05],
            "def_epa_trend_advantage": [0.04],
            "off_success_trend_difference": [0.03],
            "def_success_trend_advantage": [0.02],
        }
    )


def test_valid_artifact_passes() -> None:
    validate_recent_form_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_recent_form_features(
            pl.concat([valid(), valid()])
        )


def test_missing_column_fails() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        validate_recent_form_features(
            valid().drop("off_epa_trend_difference")
        )
