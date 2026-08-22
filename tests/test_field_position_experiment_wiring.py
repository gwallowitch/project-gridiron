from __future__ import annotations

import math

import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.validation import validate_experiments


def config(**kwargs) -> ExperimentConfig:
    values = {
        "name": "field_position_test",
        "home_field_advantage": 1.5,
        "probability_scale": 0.14,
        "margin_scale": 0.75,
        "rest_weight": 0.20,
        "off_sack_weight": 10.0,
        "punt_return_weight": 0.24,
    }
    values.update(kwargs)
    return ExperimentConfig(**values)


def test_field_position_weights_default_to_zero() -> None:
    x = ExperimentConfig("x", 1.5, 0.14)

    assert x.off_start_field_position_weight == 0.0
    assert x.def_field_position_weight == 0.0
    assert x.short_field_rate_weight == 0.0
    assert x.long_field_avoidance_weight == 0.0
    assert x.hidden_yards_field_position_weight == 0.0


def test_field_position_weights_must_be_finite() -> None:
    with pytest.raises(ValueError, match="off_start_field_position_weight"):
        validate_experiments(
            [config(off_start_field_position_weight=math.inf)]
        )


def test_field_position_weights_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="hidden_yards_field_position_weight"):
        validate_experiments(
            [config(hidden_yards_field_position_weight=-1.0)]
        )
