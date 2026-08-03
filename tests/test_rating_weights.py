from __future__ import annotations

import pytest

from gridiron.ratings.weights import (
    DEFENSE_WEIGHT,
    DISCIPLINE_WEIGHT,
    OFFENSE_WEIGHT,
    SITUATIONAL_WEIGHT,
    TOTAL_WEIGHT,
)


def test_rating_weights_total_one() -> None:
    assert TOTAL_WEIGHT == pytest.approx(1.0)


def test_unimplemented_situational_category_has_zero_weight() -> None:
    assert SITUATIONAL_WEIGHT == 0.0


def test_active_rating_weights_are_positive() -> None:
    assert OFFENSE_WEIGHT > 0
    assert DEFENSE_WEIGHT > 0
    assert DISCIPLINE_WEIGHT > 0