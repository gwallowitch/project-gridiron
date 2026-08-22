from __future__ import annotations

import math

import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.validation import validate_experiments


def config(**kwargs) -> ExperimentConfig:
    values = {
        "name": "rush_test",
        "home_field_advantage": 1.5,
        "probability_scale": 0.14,
        "margin_scale": 0.75,
        "rest_weight": 0.20,
        "off_sack_weight": 10.0,
    }
    values.update(kwargs)
    return ExperimentConfig(**values)


def test_rushing_weights_default_to_zero() -> None:
    x = ExperimentConfig("x", 1.5, 0.14)

    assert x.rush_off_epa_weight == 0.0
    assert x.rush_def_epa_weight == 0.0
    assert x.rush_success_weight == 0.0
    assert x.explosive_run_weight == 0.0


def test_rushing_weights_must_be_finite() -> None:
    with pytest.raises(ValueError, match="rush_off_epa_weight"):
        validate_experiments(
            [config(rush_off_epa_weight=math.inf)]
        )


def test_rushing_weights_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="rush_success_weight"):
        validate_experiments(
            [config(rush_success_weight=-1.0)]
        )
