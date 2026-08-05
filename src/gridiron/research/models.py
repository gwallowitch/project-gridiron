"""Data models for multi-season research."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from gridiron.experiments.models import ExperimentResult


@dataclass(frozen=True, slots=True)
class SeasonResearchResult:
    """Experiment results for one season."""

    season: int
    experiments: tuple[ExperimentResult, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "season": self.season,
            "experiments": [
                experiment.to_dict()
                for experiment in self.experiments
            ],
        }


@dataclass(frozen=True, slots=True)
class ResearchRun:
    """One completed multi-season research execution."""

    profile: str
    seasons: tuple[int, ...]
    experiment_count: int
    total_runs: int
    runtime_seconds: float
    generated_at: str
    git_commit: str | None
    python_version: str
    results: tuple[SeasonResearchResult, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        payload = asdict(self)
        payload["results"] = [
            result.to_dict()
            for result in self.results
        ]
        return payload
