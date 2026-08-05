from __future__ import annotations

import json
from pathlib import Path

from gridiron.research.models import ResearchRun
from gridiron.research.registry import append_research_registry


def run() -> ResearchRun:
    return ResearchRun(
        profile="modern",
        seasons=(2022, 2023),
        experiment_count=2,
        total_runs=4,
        runtime_seconds=1.25,
        generated_at="2026-08-05T00:00:00+00:00",
        git_commit="abc123",
        python_version="3.13.14",
        results=(),
    )


def test_registry_appends_runs(tmp_path: Path) -> None:
    path = tmp_path / "research_registry.json"

    append_research_registry(path, run())
    append_research_registry(path, run())

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert payload[0]["profile"] == "modern"
