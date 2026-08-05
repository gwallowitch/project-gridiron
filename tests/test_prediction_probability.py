from __future__ import annotations

import pytest

from gridiron.prediction.confidence import classify_confidence
from gridiron.prediction.probability import home_win_probability


def test_equal_rating_difference_is_fifty_fifty() -> None:
    assert home_win_probability(0.0) == pytest.approx(0.5)


def test_probability_increases_with_rating_difference() -> None:
    assert home_win_probability(5.0) > home_win_probability(0.0)
    assert home_win_probability(-5.0) < home_win_probability(0.0)


def test_probability_rejects_nonpositive_scale() -> None:
    with pytest.raises(ValueError, match="positive"):
        home_win_probability(1.0, scale=0.0)

@pytest.mark.parametrize(
    ("probability", "expected"),
    [(0.50, "low"), (0.60, "medium"), (0.75, "high"), (0.25, "high")],
)
def test_confidence_tiers(probability: float, expected: str) -> None:
    assert classify_confidence(probability) == expected
