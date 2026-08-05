"""Validation rules for experiment configurations."""

from __future__ import annotations

import math

from gridiron.experiments.models import ExperimentConfig


def validate_experiments(experiments: list[ExperimentConfig]) -> None:
    """Validate a collection of experiment configurations."""
    if not experiments:
        raise ValueError("At least one experiment is required.")

    names = [experiment.name for experiment in experiments]
    if len(names) != len(set(names)):
        raise ValueError("Experiment names must be unique.")

    for experiment in experiments:
        if not experiment.name.strip():
            raise ValueError("Experiment names must not be empty.")
        _require_finite(
            experiment.home_field_advantage,
            "home_field_advantage",
        )
        _require_finite(experiment.probability_scale, "probability_scale")
        _require_finite(experiment.margin_scale, "margin_scale")
        _require_finite(experiment.margin_intercept, "margin_intercept")

        if experiment.probability_scale <= 0:
            raise ValueError("probability_scale must be greater than zero.")
        if experiment.margin_scale <= 0:
            raise ValueError("margin_scale must be greater than zero.")


def _require_finite(value: float, field_name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")
