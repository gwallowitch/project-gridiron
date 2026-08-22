from __future__ import annotations

import math

import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.validation import validate_experiments


def config(**kwargs) -> ExperimentConfig:
    values = {
        "name": "third_down_test",
        "home_field_advantage": 1.5,
        "probability_scale": 0.14,
        "margin_scale": 0.75,
        "rest_weight": 0.20,
        "off_sack_weight": 10.0,
        "punt_return_weight": 0.24,
    }
    values.update(kwargs)
    return ExperimentConfig(**values)


def test_third_down_weights_default_to_zero() -> None:
    x = ExperimentConfig("x", 1.5, 0.14)

    assert x.third_down_off_epa_weight == 0.0
    assert x.third_down_def_epa_weight == 0.0
    assert x.third_down_conversion_weight == 0.0
    assert x.third_down_stop_weight == 0.0
    assert x.third_and_long_weight == 0.0


def test_third_down_weights_must_be_finite() -> None:
    with pytest.raises(ValueError, match="third_down_off_epa_weight"):
        validate_experiments(
            [config(third_down_off_epa_weight=math.inf)]
        )


def test_third_down_weights_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="third_and_long_weight"):
        validate_experiments(
            [config(third_and_long_weight=-1.0)]
        )
