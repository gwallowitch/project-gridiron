"""Validation rules for experiment configurations."""
from __future__ import annotations

import math

from gridiron.experiments.models import ExperimentConfig


def validate_experiments(experiments: list[ExperimentConfig]) -> None:
    if not experiments:
        raise ValueError("At least one experiment is required.")
    names = [e.name for e in experiments]
    if len(names) != len(set(names)):
        raise ValueError("Experiment names must be unique.")
    for e in experiments:
        if not e.name.strip():
            raise ValueError("Experiment names must not be empty.")
        for value, name in (
            (e.home_field_advantage, "home_field_advantage"),
            (e.probability_scale, "probability_scale"),
            (e.margin_scale, "margin_scale"),
            (e.margin_intercept, "margin_intercept"),
            (e.rest_weight, "rest_weight"),
            (e.qb_weight, "qb_weight"),
            (e.injury_weight, "injury_weight"),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")
        if e.probability_scale <= 0:
            raise ValueError("probability_scale must be greater than zero.")
        if e.margin_scale <= 0:
            raise ValueError("margin_scale must be greater than zero.")
        if e.injury_weight < 0:
            raise ValueError("injury_weight must not be negative.")
