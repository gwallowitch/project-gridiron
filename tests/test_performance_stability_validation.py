import polars as pl
import pytest

from gridiron.validation.performance_stability_features import (
    validate_performance_stability_features,
)


def valid() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g"],
            "season": [2025],
            "week": [3],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_mean_point_differential": [5.0],
            "away_mean_point_differential": [-2.0],
            "home_point_differential_std": [6.0],
            "away_point_differential_std": [8.0],
            "home_mean_absolute_margin": [10.0],
            "away_mean_absolute_margin": [12.0],
            "home_close_game_rate": [0.5],
            "away_close_game_rate": [0.25],
            "home_performance_stability_known": [True],
            "away_performance_stability_known": [True],
            "stability_advantage": [2.0],
            "recent_margin_advantage": [7.0],
            "close_game_experience_advantage": [0.25],
        }
    )


def test_validation_accepts_valid_frame() -> None:
    validate_performance_stability_features(valid())


def test_duplicate_game_fails() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        validate_performance_stability_features(
            pl.concat([valid(), valid()])
        )


def test_close_game_rate_bounds_are_enforced() -> None:
    frame = valid().with_columns(
        pl.lit(1.2).alias("home_close_game_rate")
    )

    with pytest.raises(ValueError, match="between 0 and 1"):
        validate_performance_stability_features(frame)
