import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path("scripts/validate_step88c_locked_model_calibration.py")
SPEC = importlib.util.spec_from_file_location("step88c", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_88c_metrics_are_valid() -> None:
    p = np.array([0.8, 0.7, 0.4, 0.2])
    y = np.array([1.0, 0.0, 1.0, 0.0])
    m = M._metrics(p, y)
    assert m["games"] == 4
    assert 0.0 <= m["accuracy"] <= 1.0
    assert 0.0 <= m["brier"] <= 1.0
    assert m["log_loss"] >= 0.0
    assert m["ece"] >= 0.0


def test_88c_temperature_preserves_half_threshold() -> None:
    p = np.array([0.2, 0.4, 0.6, 0.8])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    cal = M._fit_temperature(p, y)
    out = cal.transform(p)
    assert np.array_equal(out >= 0.5, p >= 0.5)


def test_88c_logistic_outputs_probabilities() -> None:
    p = np.array([0.15, 0.25, 0.45, 0.55, 0.75, 0.85])
    y = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
    cal = M._fit_logistic(p, y)
    out = cal.transform(p)
    assert np.all(out > 0.0)
    assert np.all(out < 1.0)


def test_88c_ece_perfect_predictions_is_zero() -> None:
    p = np.array([0.0, 0.0, 1.0, 1.0])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    assert M._ece(p, y) == 0.0
