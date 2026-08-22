"""TOML configuration loading for experiments."""
from __future__ import annotations

import tomllib
from pathlib import Path

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.validation import validate_experiments


def load_experiments(path: Path) -> list[ExperimentConfig]:
    if not path.exists():
        raise FileNotFoundError(
            f"Experiment configuration does not exist: {path}"
        )

    with path.open("rb") as handle:
        payload = tomllib.load(handle)

    field_names = ExperimentConfig.__dataclass_fields__
    experiments = []
    for row in payload.get("experiment", []):
        values = {}
        for name in field_names:
            if name == "name":
                values[name] = str(row[name])
            elif name in {"home_field_advantage", "probability_scale"}:
                values[name] = float(row[name])
            else:
                values[name] = float(
                    row.get(name, field_names[name].default)
                )
        experiments.append(ExperimentConfig(**values))

    validate_experiments(experiments)
    return experiments
