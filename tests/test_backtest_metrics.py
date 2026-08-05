from __future__ import annotations

import math

import pytest

from gridiron.backtest.metrics import (
    binary_log_loss,
    brier_score,
    mean_absolute_error,
    root_mean_squared_error,
    winner_accuracy,
)


def test_winner_accuracy() -> None:
    assert winner_accuracy(["A", "B", "C"], ["A", "C", "C"]) == pytest.approx(2 / 3)


def test_brier_score() -> None:
    assert brier_score([0.8, 0.2], [1.0, 0.0]) == pytest.approx(0.04)


def test_log_loss_is_finite_at_probability_boundaries() -> None:
    assert math.isfinite(binary_log_loss([1.0, 0.0], [1.0, 0.0]))


def test_margin_errors() -> None:
    predicted = [3.0, -2.0]
    actual = [1.0, 2.0]
    assert mean_absolute_error(predicted, actual) == pytest.approx(3.0)
    assert root_mean_squared_error(predicted, actual) == pytest.approx(math.sqrt(10.0))


def test_metrics_reject_empty_inputs() -> None:
    with pytest.raises(ValueError, match="at least one"):
        winner_accuracy([], [])
