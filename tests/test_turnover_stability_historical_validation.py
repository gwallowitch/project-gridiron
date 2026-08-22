from pathlib import Path

import polars as pl
import pytest

from scripts.validate_turnover_stability_features import (
    SeasonValidation,
    _validate_cross_season,
    validate_season,
)

FEATURES = (
    "turnover_protection_advantage",
    "takeaway_creation_advantage",
    "interception_protection_advantage",
    "interception_creation_advantage",
    "off_fumble_luck_advantage",
    "def_fumble_luck_advantage",
    "combined_fumble_recovery_luck",
)


def artifact() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2024, 2024],
            "home_turnover_stability_known": [True, True],
            "away_turnover_stability_known": [True, True],
            "turnover_protection_advantage": [0.01, -0.01],
            "takeaway_creation_advantage": [0.02, -0.02],
            "interception_protection_advantage": [0.01, -0.01],
            "interception_creation_advantage": [0.02, -0.02],
            "off_fumble_luck_advantage": [0.10, -0.10],
            "def_fumble_luck_advantage": [0.12, -0.12],
            "combined_fumble_recovery_luck": [0.22, -0.22],
            "home_off_turnover_eligible_plays": [240, 260],
            "away_off_turnover_eligible_plays": [240, 260],
            "home_def_turnover_eligible_plays_faced": [240, 260],
            "away_def_turnover_eligible_plays_faced": [240, 260],
            "home_off_fumbles": [8, 10],
            "away_off_fumbles": [8, 10],
            "home_def_opponent_fumbles": [8, 10],
            "away_def_opponent_fumbles": [8, 10],
            "home_turnover_stability_history_weeks": [6, 7],
            "away_turnover_stability_history_weeks": [6, 7],
        }
    )


def test_validate_season_accepts_valid_artifact(
    tmp_path: Path,
) -> None:
    path = tmp_path / "turnover_stability_features_2024.parquet"
    artifact().write_parquet(path)

    result = validate_season(path, 2024)

    assert result.rows == 2
    assert result.home_known == 1.0
    assert result.feature_coverage[
        "turnover_protection_advantage"
    ] == 1.0


def test_validate_season_rejects_duplicate_game_id(
    tmp_path: Path,
) -> None:
    path = tmp_path / "turnover_stability_features_2024.parquet"
    artifact().with_columns(
        pl.lit("g1").alias("game_id")
    ).write_parquet(path)

    with pytest.raises(ValueError, match="duplicate"):
        validate_season(path, 2024)


def result(
    *,
    home_known: float = 0.95,
    skill_coverage: float = 0.95,
    luck_coverage: float = 0.80,
    off_plays: float = 250.0,
    fumbles: float = 8.0,
    history: float = 8.0,
) -> SeasonValidation:
    coverage = {
        "turnover_protection_advantage": skill_coverage,
        "takeaway_creation_advantage": skill_coverage,
        "interception_protection_advantage": skill_coverage,
        "interception_creation_advantage": skill_coverage,
        "off_fumble_luck_advantage": luck_coverage,
        "def_fumble_luck_advantage": luck_coverage,
        "combined_fumble_recovery_luck": luck_coverage,
    }

    return SeasonValidation(
        season=2024,
        rows=285,
        home_known=home_known,
        away_known=0.95,
        feature_coverage=coverage,
        feature_mean={c: 0.0 for c in FEATURES},
        feature_std={c: 0.1 for c in FEATURES},
        sample_means={
            "home_off_turnover_eligible_plays": off_plays,
            "away_off_turnover_eligible_plays": 250.0,
            "home_def_turnover_eligible_plays_faced": 250.0,
            "away_def_turnover_eligible_plays_faced": 250.0,
            "home_off_fumbles": fumbles,
            "away_off_fumbles": 8.0,
            "home_def_opponent_fumbles": 8.0,
            "away_def_opponent_fumbles": 8.0,
            "home_turnover_stability_history_weeks": history,
            "away_turnover_stability_history_weeks": 8.0,
        },
    )


def test_low_known_coverage_fails() -> None:
    with pytest.raises(ValueError, match="below 90%"):
        _validate_cross_season([
            result(home_known=0.80)
        ])


def test_low_skill_coverage_fails() -> None:
    with pytest.raises(ValueError, match="below 85%"):
        _validate_cross_season([
            result(skill_coverage=0.70)
        ])


def test_luck_features_use_sparse_coverage_gate() -> None:
    _validate_cross_season([
        result(luck_coverage=0.70)
    ])

    with pytest.raises(ValueError, match="below 65%"):
        _validate_cross_season([
            result(luck_coverage=0.55)
        ])


def test_low_play_depth_fails() -> None:
    with pytest.raises(ValueError, match="offensive turnover-play"):
        _validate_cross_season([
            result(off_plays=100.0)
        ])


def test_low_fumble_depth_fails() -> None:
    with pytest.raises(ValueError, match="fumble sample"):
        _validate_cross_season([
            result(fumbles=2.0)
        ])


def test_low_history_depth_fails() -> None:
    with pytest.raises(ValueError, match="history depth"):
        _validate_cross_season([
            result(history=3.0)
        ])
