"""Serializable benchmark history records."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from gridiron.benchmark.models import BenchmarkResult


def append_benchmark_history(
    result: BenchmarkResult,
    output_path: Path,
) -> None:
    """Append one benchmark result to a JSON Lines history file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(asdict(result), sort_keys=True))
        stream.write("\n")
