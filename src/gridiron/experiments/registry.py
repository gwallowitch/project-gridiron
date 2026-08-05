"""Persistent JSON registry for experiment results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gridiron.experiments.models import ExperimentResult


def load_registry(path: Path) -> list[dict[str, Any]]:
    """Load all registry records, returning an empty list when absent."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise TypeError("Experiment registry must contain a JSON list.")
    return payload


def append_registry(
    path: Path,
    results: list[ExperimentResult],
) -> None:
    """Append experiment results to the registry atomically."""
    records = load_registry(path)
    records.extend(result.to_dict() for result in results)

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary_path.replace(path)
