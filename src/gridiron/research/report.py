"""Console reporting for multi-season research."""

from __future__ import annotations

from gridiron.research.aggregation import (
    ResearchAggregate,
    aggregate_research,
)
from gridiron.research.models import ResearchRun


def format_research_report(run: ResearchRun) -> str:
    """Return a research execution and aggregate report."""
    season_text = ", ".join(str(season) for season in run.seasons)
    aggregates = aggregate_research(run)

    lines = [
        "=" * 96,
        "PROJECT GRIDIRON RESEARCH".center(96),
        "=" * 96,
        f"Profile.................. {run.profile}",
        f"Seasons.................. {season_text}",
        f"Experiments per season... {run.experiment_count}",
        f"Total experiment runs.... {run.total_runs}",
        f"Runtime.................. {run.runtime_seconds:.2f} s",
        "-" * 96,
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
            "-" * 96,
            "CROSS-SEASON AGGREGATE RANKING",
            "-" * 96,
            (
                "Rank  Experiment          Acc.    Brier   LogLoss  "
                "MAE     RMSE    Score    Wins  ΔBaseline"
            ),
            "-" * 96,
        ]
    )

    for rank, aggregate in enumerate(aggregates, start=1):
        lines.append(
            _format_aggregate_row(rank, aggregate)
        )

    winner = aggregates[0]
    lines.extend(
        [
            "-" * 96,
            f"Recommended aggregate leader: {winner.name}",
            (
                "Negative ΔBaseline means a lower average selection "
                "score than baseline."
            ),
            "=" * 96,
        ]
    )
    return "\n".join(lines)


def _format_aggregate_row(
    rank: int,
    aggregate: ResearchAggregate,
) -> str:
    return (
        f"{rank:>4}  "
        f"{aggregate.name:<18}"
        f"{aggregate.average_winner_accuracy:>7.1%}"
        f"{aggregate.average_brier_score:>9.4f}"
        f"{aggregate.average_log_loss:>9.4f}"
        f"{aggregate.average_margin_mae:>8.2f}"
        f"{aggregate.average_margin_rmse:>8.2f}"
        f"{aggregate.average_selection_score:>9.4f}"
        f"{aggregate.season_wins:>6}"
        f"{aggregate.baseline_score_delta:>11.4f}"
    )


def print_research_report(run: ResearchRun) -> None:
    """Print a multi-season research report."""
    print(format_research_report(run))
