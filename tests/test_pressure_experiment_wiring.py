from __future__ import annotations

import math

import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.validation import validate_experiments


def config(**kwargs) -> ExperimentConfig:
    values = {
        "name": "pressure_test",
        "home_field_advantage": 1.5,
        "probability_scale": 0.14,
        "margin_scale": 0.75,
        "rest_weight": 0.20,
        "off_sack_weight": 10.0,
        "punt_return_weight": 0.24,
    }
    values.update(kwargs)
    return ExperimentConfig(**values)


def test_pressure_weights_default_to_zero() -> None:
    x = ExperimentConfig("x", 1.5, 0.14)

    assert x.pass_protection_weight == 0.0
    assert x.pressure_creation_weight == 0.0
    assert x.clean_dropback_weight == 0.0
    assert x.pressured_off_epa_weight == 0.0
    assert x.pressured_def_epa_weight == 0.0


def test_pressure_weights_must_be_finite() -> None:
    with pytest.raises(ValueError, match="pass_protection_weight"):
        validate_experiments(
            [config(pass_protection_weight=math.inf)]
        )


def test_pressure_weights_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="pressured_def_epa_weight"):
        validate_experiments(
            [config(pressured_def_epa_weight=-1.0)]
        )
