"""TOML configuration loading for experiments."""

from __future__ import annotations

import tomllib
from pathlib import Path

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.validation import validate_experiments


def load_experiments(path: Path) -> list[ExperimentConfig]:
    """Load and validate experiment definitions from TOML."""
    if not path.exists():
        raise FileNotFoundError(f"Experiment configuration does not exist: {path}")

    with path.open("rb") as handle:
        payload = tomllib.load(handle)

    rows = payload.get("experiment", [])
    experiments = [
        ExperimentConfig(
            name=str(row["name"]),
            home_field_advantage=float(row["home_field_advantage"]),
            probability_scale=float(row["probability_scale"]),
            margin_scale=float(row.get("margin_scale", 1.0)),
            margin_intercept=float(row.get("margin_intercept", 0.0)),
        )
        for row in rows
    ]
    validate_experiments(experiments)
    return experiments
