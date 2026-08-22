import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path("scripts/validate_step88d_calibration_robustness.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_step88d_calibration_robustness",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_parameter_stats_are_nonnegative() -> None:
    folds = [
        {"parameters": {"intercept": 0.0, "slope": 0.8}},
        {"parameters": {"intercept": 0.0, "slope": 0.9}},
        {"parameters": {"intercept": 0.0, "slope": 1.0}},
        {"parameters": {"intercept": 0.0, "slope": 1.1}},
    ]

    stats = M._parameter_stats(folds)

    assert stats["slope_range"] >= 0.0
    assert stats["slope_std"] >= 0.0
    assert stats["intercept_range"] == 0.0


def test_probability_diagnostics_detect_no_winner_flips() -> None:
    raw = np.array([0.2, 0.4, 0.6, 0.8])
    calibrated = np.array([0.3, 0.45, 0.55, 0.7])
    y = np.array([0.0, 0.0, 1.0, 1.0])

    result = M._probability_diagnostics(
        raw,
        calibrated,
        y,
    )

    assert result["winner_flip_rate"] == 0.0


def test_selection_score_prefers_lower_loss() -> None:
    better = {
        "aggregate": {
            "accuracy": 0.60,
            "brier": 0.22,
            "log_loss": 0.64,
            "ece": 0.05,
        }
    }
    worse = {
        "aggregate": {
            "accuracy": 0.60,
            "brier": 0.24,
            "log_loss": 0.67,
            "ece": 0.08,
        }
    }

    assert M._selection_score(better) < M._selection_score(worse)


def test_expected_fingerprint_is_locked() -> None:
    assert len(M.EXPECTED_FINGERPRINT) == 64
