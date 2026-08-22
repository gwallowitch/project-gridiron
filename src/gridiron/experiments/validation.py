"""Validation rules for experiment configurations."""
from __future__ import annotations

import math
from dataclasses import fields

from gridiron.experiments.models import ExperimentConfig

_ALLOWED_NEGATIVE = {"margin_intercept"}


def validate_experiments(
    experiments: list[ExperimentConfig],
) -> None:
    if not experiments:
        raise ValueError("At least one experiment is required.")

    names = [experiment.name for experiment in experiments]
    if len(names) != len(set(names)):
        raise ValueError("Experiment names must be unique.")

    numeric_fields = [
        field.name
        for field in fields(ExperimentConfig)
        if field.name != "name"
    ]

    for experiment in experiments:
        if not experiment.name.strip():
            raise ValueError(
                "Experiment names must not be empty."
            )

        for name in numeric_fields:
            value = getattr(experiment, name)
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")

        if experiment.probability_scale <= 0:
            raise ValueError(
                "probability_scale must be greater than zero."
            )
        if experiment.margin_scale <= 0:
            raise ValueError(
                "margin_scale must be greater than zero."
            )

        nonnegative = [
            name
            for name in numeric_fields
            if name not in {
                "home_field_advantage",
                "probability_scale",
                "margin_scale",
                *_ALLOWED_NEGATIVE,
            }
        ]
        for name in nonnegative:
            if getattr(experiment, name) < 0:
                raise ValueError(
                    f"{name} must not be negative."
                )
