import importlib.util
import sys
from pathlib import Path

import polars as pl

SCRIPT = Path("scripts/validate_step88b_combined_model_diagnostics.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_step88b_combined_model_diagnostics",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def sample() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["a", "b", "c", "d"],
            "model_home_win_probability": [0.8, 0.7, 0.4, 0.2],
            "actual_home_win": [1.0, 0.0, 1.0, 0.0],
            "predicted_margin": [7.0, 4.0, -2.0, -6.0],
            "actual_margin": [10.0, -3.0, 1.0, -7.0],
        }
    )


def test_88b_season_metrics_are_bounded() -> None:
    metrics = MODULE._season_metrics(sample())

    assert metrics["games"] == 4
    assert 0.0 <= metrics["winner_accuracy"] <= 1.0
    assert 0.0 <= metrics["brier_score"] <= 1.0
    assert metrics["log_loss"] >= 0.0
    assert metrics["margin_mae"] is not None
    assert metrics["margin_rmse"] is not None


def test_88b_calibration_buckets_cover_rows() -> None:
    buckets = MODULE._calibration_buckets(sample())

    assert sum(row["games"] for row in buckets) == 4


def test_88b_ece_is_nonnegative() -> None:
    buckets = MODULE._calibration_buckets(sample())

    assert MODULE._expected_calibration_error(buckets) >= 0.0


def test_88b_split_metrics_include_core_splits() -> None:
    splits = MODULE._split_metrics(sample())

    assert "model_home_favorite" in splits
    assert "model_away_favorite" in splits
    assert "high_confidence" in splits
    assert "close_probability" in splits
