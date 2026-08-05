"""Console reporting for multi-season research."""

from __future__ import annotations

from gridiron.research.models import ResearchRun


def format_research_report(run: ResearchRun) -> str:
    """Return a compact research execution report."""
    season_text = ", ".join(str(season) for season in run.seasons)
    lines = [
        "=" * 72,
        "PROJECT GRIDIRON RESEARCH".center(72),
        "=" * 72,
        f"Profile.................. {run.profile}",
        f"Seasons.................. {season_text}",
        f"Experiments per season... {run.experiment_count}",
        f"Total experiment runs.... {run.total_runs}",
        f"Runtime.................. {run.runtime_seconds:.2f} s",
        "-" * 72,
    ]
    for season_result in run.results:
        best = season_result.experiments[0]
        lines.append(
            f"{season_result.season}: "
            f"{len(season_result.experiments)} experiments, "
            f"best={best.name}, "
            f"score={best.selection_score:.4f}"
        )
    lines.extend(
        [
            "-" * 72,
            "Research execution complete.",
            "=" * 72,
        ]
    )
    return "\n".join(lines)


def print_research_report(run: ResearchRun) -> None:
    """Print a multi-season research report."""
    print(format_research_report(run))
