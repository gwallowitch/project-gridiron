from __future__ import annotations

import math

import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.validation import validate_experiments


def test_qb_weight_defaults_to_zero() -> None:
    config = ExperimentConfig("baseline", 1.5, 0.14)
    assert config.qb_weight == 0.0

def test_qb_weight_must_be_finite() -> None:
    config = ExperimentConfig("bad", 1.5, 0.14, qb_weight=math.inf)
    with pytest.raises(ValueError, match="qb_weight"):
        validate_experiments([config])
