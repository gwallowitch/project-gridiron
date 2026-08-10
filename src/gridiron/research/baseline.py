"""Baseline resolution for research experiment sets."""

from __future__ import annotations

from gridiron.research.models import ResearchRun


def resolve_baseline_name(
    run: ResearchRun,
    baseline_name: str | None = None,
) -> str:
    """Return an explicit or uniquely inferred baseline experiment name."""
    names = {
        experiment.name
        for season_result in run.results
        for experiment in season_result.experiments
    }

    if baseline_name is not None:
        if baseline_name not in names:
            raise ValueError(
                f"Baseline experiment {baseline_name!r} was not found."
            )
        return baseline_name

    candidates = sorted(
        name for name in names if name.endswith("_baseline")
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(
            "No baseline experiment was found. "
            "Use a name ending in '_baseline'."
        )
    raise ValueError(
        "Multiple baseline experiments were found: "
        + ", ".join(candidates)
    )
