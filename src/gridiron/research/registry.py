"""Persistence for multi-season research runs."""

from __future__ import annotations

import json
from pathlib import Path

from gridiron.research.models import ResearchRun


def append_research_registry(
    path: Path,
    run: ResearchRun,
) -> Path:
    """Append one research run to a JSON registry."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise TypeError(
                "Research registry must contain a JSON list."
            )
    else:
        payload = []

    payload.append(run.to_dict())
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)
    return path
