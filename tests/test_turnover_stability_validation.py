import polars as pl
import pytest

from gridiron.validation.turnover_stability_features import (
    validate_turnover_stability_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_turnover_stability_known": [True],
            "away_turnover_stability_known": [True],
            "home_turnover_stability_history_weeks": [1],
            "away_turnover_stability_history_weeks": [1],
            "turnover_protection_advantage": [0.01],
            "takeaway_creation_advantage": [0.02],
            "interception_protection_advantage": [0.03],
            "interception_creation_advantage": [0.04],
            "off_fumble_luck_advantage": [0.05],
            "def_fumble_luck_advantage": [0.06],
            "combined_fumble_recovery_luck": [0.07],
        }
    )


def test_valid_artifact_passes() -> None:
    validate_turnover_stability_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_turnover_stability_features(
            pl.concat([valid(), valid()])
        )


def test_missing_column_fails() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        validate_turnover_stability_features(
            valid().drop("turnover_protection_advantage")
        )
