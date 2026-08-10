"""Cross-season aggregation for Project Gridiron research."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import fmean

from gridiron.research.baseline import resolve_baseline_name
from gridiron.research.models import ResearchRun


@dataclass(frozen=True, slots=True)
class ResearchAggregate:
    """Cross-season summary for one experiment."""

    name: str
    seasons: int
    season_wins: int
    average_winner_accuracy: float
    average_brier_score: float
    average_log_loss: float
    average_margin_mae: float
    average_margin_rmse: float
    average_selection_score: float
    best_season: int
    best_season_score: float
    worst_season: int
    worst_season_score: float
    baseline_score_delta: float


def aggregate_research(
    run: ResearchRun,
    *,
    baseline_name: str | None = None,
) -> tuple[ResearchAggregate, ...]:
    """Aggregate experiment performance across all seasons."""
    grouped = defaultdict(list)
    season_winners: dict[int, str] = {}

    for season_result in run.results:
        if not season_result.experiments:
            raise ValueError(
                f"Season {season_result.season} has no experiment results."
            )
        season_winners[season_result.season] = (
            season_result.experiments[0].name
        )
        for experiment in season_result.experiments:
            grouped[experiment.name].append(
                (season_result.season, experiment)
            )

    if not grouped:
        raise ValueError("Research run contains no experiment results.")

    resolved_baseline = resolve_baseline_name(run, baseline_name)
    baseline_rows = grouped[resolved_baseline]
    baseline_average = fmean(
        result.selection_score
        for _, result in baseline_rows
    )

    aggregates = []
    for name, rows in grouped.items():
        scores = [
            result.selection_score
            for _, result in rows
        ]
        best_season, best_result = min(
            rows,
            key=lambda row: row[1].selection_score,
        )
        worst_season, worst_result = max(
            rows,
            key=lambda row: row[1].selection_score,
        )
        average_score = fmean(scores)

        aggregates.append(
            ResearchAggregate(
                name=name,
                seasons=len(rows),
                season_wins=sum(
                    winner == name
                    for winner in season_winners.values()
                ),
                average_winner_accuracy=fmean(
                    result.winner_accuracy
                    for _, result in rows
                ),
                average_brier_score=fmean(
                    result.brier_score
                    for _, result in rows
                ),
                average_log_loss=fmean(
                    result.log_loss
                    for _, result in rows
                ),
                average_margin_mae=fmean(
                    result.margin_mae
                    for _, result in rows
                ),
                average_margin_rmse=fmean(
                    result.margin_rmse
                    for _, result in rows
                ),
                average_selection_score=average_score,
                best_season=best_season,
                best_season_score=best_result.selection_score,
                worst_season=worst_season,
                worst_season_score=worst_result.selection_score,
                baseline_score_delta=(
                    average_score - baseline_average
                ),
            )
        )

    return tuple(
        sorted(
            aggregates,
            key=lambda item: (
                item.average_selection_score,
                -item.average_winner_accuracy,
                item.average_brier_score,
                item.name,
            ),
        )
    )
