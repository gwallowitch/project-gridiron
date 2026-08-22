from __future__ import annotations

import math

import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.validation import validate_experiments


def config(**kwargs) -> ExperimentConfig:
    values = {
        "name": "recent_form_test",
        "home_field_advantage": 1.5,
        "probability_scale": 0.14,
        "margin_scale": 0.75,
        "rest_weight": 0.20,
        "off_sack_weight": 10.0,
        "punt_return_weight": 0.24,
        "long_field_avoidance_weight": 1.0,
    }
    values.update(kwargs)
    return ExperimentConfig(**values)


def test_recent_form_weights_default_to_zero() -> None:
    x = ExperimentConfig("x", 1.5, 0.14)

    assert x.recent_off_epa_weight == 0.0
    assert x.recent_def_epa_weight == 0.0
    assert x.off_epa_trend_weight == 0.0
    assert x.def_epa_trend_weight == 0.0
    assert x.off_success_trend_weight == 0.0
    assert x.def_success_trend_weight == 0.0


def test_recent_form_weights_must_be_finite() -> None:
    with pytest.raises(
        ValueError,
        match="recent_off_epa_weight",
    ):
        validate_experiments(
            [config(recent_off_epa_weight=math.inf)]
        )


def test_recent_form_weights_must_not_be_negative() -> None:
    with pytest.raises(
        ValueError,
        match="def_success_trend_weight",
    ):
        validate_experiments(
            [config(def_success_trend_weight=-1.0)]
        )


def test_78c_preserves_current_four_weight_lock() -> None:
    x = config()

    assert x.rest_weight == 0.20
    assert x.off_sack_weight == 10.0
    assert x.punt_return_weight == 0.24
    assert x.long_field_avoidance_weight == 1.0


def test_78c_keeps_rejected_families_zero_by_default() -> None:
    x = config()

    assert x.fourth_down_off_epa_weight == 0.0
    assert x.explosive_off_rate_weight == 0.0
    assert x.turnover_protection_weight == 0.0
    assert x.takeaway_creation_weight == 0.0
