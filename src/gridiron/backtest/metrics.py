"""Pure metric calculations for Project Gridiron backtests."""

from __future__ import annotations

import math
from collections.abc import Iterable


def winner_accuracy(predicted: Iterable[str], actual: Iterable[str]) -> float:
    """Return the fraction of correctly predicted winners."""
    pairs = list(zip(predicted, actual, strict=True))
    if not pairs:
        raise ValueError("Winner accuracy requires at least one game.")
    return sum(left == right for left, right in pairs) / len(pairs)


def brier_score(probabilities: Iterable[float], outcomes: Iterable[float]) -> float:
    """Return binary Brier score; lower is better."""
    pairs = list(zip(probabilities, outcomes, strict=True))
    if not pairs:
        raise ValueError("Brier score requires at least one game.")
    _validate_probabilities(value for value, _ in pairs)
    return sum((probability - outcome) ** 2 for probability, outcome in pairs) / len(pairs)


def binary_log_loss(
    probabilities: Iterable[float],
    outcomes: Iterable[float],
    *,
    epsilon: float = 1e-15,
) -> float:
    """Return binary logarithmic loss with numerical clipping."""
    pairs = list(zip(probabilities, outcomes, strict=True))
    if not pairs:
        raise ValueError("Log loss requires at least one game.")
    _validate_probabilities(value for value, _ in pairs)
    if not 0 < epsilon < 0.5:
        raise ValueError("epsilon must be between 0 and 0.5.")

    total = 0.0
    for probability, outcome in pairs:
        clipped = min(max(probability, epsilon), 1.0 - epsilon)
        total -= outcome * math.log(clipped)
        total -= (1.0 - outcome) * math.log(1.0 - clipped)
    return total / len(pairs)


def mean_absolute_error(predicted: Iterable[float], actual: Iterable[float]) -> float:
    """Return mean absolute error."""
    pairs = list(zip(predicted, actual, strict=True))
    if not pairs:
        raise ValueError("MAE requires at least one observation.")
    return sum(abs(left - right) for left, right in pairs) / len(pairs)


def root_mean_squared_error(
    predicted: Iterable[float], actual: Iterable[float]
) -> float:
    """Return root mean squared error."""
    pairs = list(zip(predicted, actual, strict=True))
    if not pairs:
        raise ValueError("RMSE requires at least one observation.")
    return math.sqrt(sum((left - right) ** 2 for left, right in pairs) / len(pairs))


def _validate_probabilities(values: Iterable[float]) -> None:
    for value in values:
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("Probabilities must be finite values between 0 and 1.")
