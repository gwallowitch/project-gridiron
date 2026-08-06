"""Console reporting for multi-season research."""

from __future__ import annotations

from gridiron.research.aggregation import (
    ResearchAggregate,
    aggregate_research,
)
from gridiron.research.models import ResearchRun
from gridiron.research.promotion import review_candidate
from gridiron.research.statistics import analyze_candidates


def format_research_report(run: ResearchRun) -> str:
    """Return research, aggregate, and promotion reporting."""
    season_text = ", ".join(str(season) for season in run.seasons)
    aggregates = aggregate_research(run)
    analyses = analyze_candidates(run)

    lines = [
        "=" * 104,
        "PROJECT GRIDIRON RESEARCH".center(104),
        "=" * 104,
        f"Profile.................. {run.profile}",
        f"Seasons.................. {season_text}",
        f"Experiments per season... {run.experiment_count}",
        f"Total experiment runs.... {run.total_runs}",
        f"Runtime.................. {run.runtime_seconds:.2f} s",
        "-" * 104,
    ]

    for season_result in run.results:
        best = season_result.experiments[0]
        lines.append(
            f"{season_result.season}: "
            f"{len(season_result.experiments)} experiments, "
            f"best={best.name}, score={best.selection_score:.4f}"
        )

    lines.extend(
        [
            "-" * 104,
            "CROSS-SEASON AGGREGATE RANKING",
            "-" * 104,
            (
                "Rank  Experiment          Acc.    Brier   LogLoss  "
                "MAE     RMSE    Score    Wins  DeltaBase"
            ),
            "-" * 104,
        ]
    )
    for rank, aggregate in enumerate(aggregates, start=1):
        lines.append(_format_aggregate_row(rank, aggregate))

    lines.extend(
        [
            "-" * 104,
            "PAIRED STATISTICAL VALIDATION",
            "-" * 104,
            (
                "Candidate          W-L-T  MeanDelta Median    StdDev   "
                "95% CI                  AccDelta"
            ),
            "-" * 104,
        ]
    )
    for analysis in analyses:
        lines.append(
            f"{analysis.name:<18}"
            f"{analysis.wins:>2}-{analysis.losses}-{analysis.ties:<3}"
            f"{analysis.mean_score_delta:>10.4f}"
            f"{analysis.median_score_delta:>10.4f}"
            f"{analysis.score_delta_stddev:>9.4f}"
            f"  [{analysis.confidence_interval_low:>7.4f}, "
            f"{analysis.confidence_interval_high:>7.4f}]"
            f"{analysis.mean_accuracy_delta:>10.1%}"
        )

    leader = aggregates[0]
    leader_analysis = next(
        item for item in analyses if item.name == leader.name
    )
    review = review_candidate(leader_analysis)
    lines.extend(
        [
            "-" * 104,
            "PROMOTION REVIEW",
            "-" * 104,
            f"Candidate................. {review.candidate}",
            f"Status.................... {review.status}",
            f"Mean score delta.......... {leader_analysis.mean_score_delta:.4f}",
            (
                "95% confidence interval.. "
                f"[{leader_analysis.confidence_interval_low:.4f}, "
                f"{leader_analysis.confidence_interval_high:.4f}]"
            ),
            (
                "Season record............ "
                f"{leader_analysis.wins}-"
                f"{leader_analysis.losses}-"
                f"{leader_analysis.ties}"
            ),
            f"Mean accuracy delta....... {leader_analysis.mean_accuracy_delta:+.1%}",
            f"Reason.................... {review.reason}",
            "-" * 104,
            (
                "Negative score deltas favor the candidate; positive "
                "accuracy deltas favor the candidate."
            ),
            "=" * 104,
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
