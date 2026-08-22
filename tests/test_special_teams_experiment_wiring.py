from __future__ import annotations

import math

import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.validation import validate_experiments


def config(**kwargs) -> ExperimentConfig:
    values = {
        "name": "special_teams_test",
        "home_field_advantage": 1.5,
        "probability_scale": 0.14,
        "margin_scale": 0.75,
        "rest_weight": 0.20,
        "off_sack_weight": 10.0,
    }
    values.update(kwargs)
    return ExperimentConfig(**values)


def test_special_teams_weights_default_to_zero() -> None:
    x = ExperimentConfig("x", 1.5, 0.14)

    assert x.fg_make_rate_weight == 0.0
    assert x.punt_coverage_weight == 0.0
    assert x.punt_return_weight == 0.0
    assert x.punt_touchback_weight == 0.0


def test_special_teams_weights_must_be_finite() -> None:
    with pytest.raises(ValueError, match="fg_make_rate_weight"):
        validate_experiments(
            [config(fg_make_rate_weight=math.inf)]
        )


def test_special_teams_weights_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="punt_return_weight"):
        validate_experiments(
            [config(punt_return_weight=-1.0)]
        )
