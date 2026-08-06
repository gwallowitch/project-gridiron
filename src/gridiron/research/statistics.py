"""Paired statistical analysis for Project Gridiron research."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from statistics import fmean, median, stdev

from gridiron.research.models import ResearchRun


@dataclass(frozen=True, slots=True)
class CandidateStatistics:
    """Paired cross-season differences versus the baseline."""

    name: str
    seasons: int
    wins: int
    losses: int
    ties: int
    mean_score_delta: float
    median_score_delta: float
    score_delta_stddev: float
    confidence_interval_low: float
    confidence_interval_high: float
    mean_accuracy_delta: float
    mean_brier_delta: float
    mean_log_loss_delta: float
    mean_margin_mae_delta: float
    mean_margin_rmse_delta: float


def analyze_candidates(
    run: ResearchRun,
    *,
    baseline_name: str = "rest_000_baseline",
    bootstrap_samples: int = 10_000,
    confidence_level: float = 0.95,
    random_seed: int = 60,
    tie_tolerance: float = 1e-12,
) -> tuple[CandidateStatistics, ...]:
    """Analyze every non-baseline experiment against baseline."""
    if bootstrap_samples < 100:
        raise ValueError("Bootstrap samples must be at least 100.")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("Confidence level must be between 0 and 1.")

    by_name: dict[str, dict[int, object]] = {}
    for season_result in run.results:
        for result in season_result.experiments:
            by_name.setdefault(result.name, {})[
                season_result.season
            ] = result

    baseline = by_name.get(baseline_name)
    if baseline is None:
        raise ValueError(
            f"Baseline experiment {baseline_name!r} was not found."
        )

    analyses: list[CandidateStatistics] = []
    for name, candidate in by_name.items():
        if name == baseline_name:
            continue

        seasons = sorted(set(baseline).intersection(candidate))
        if len(seasons) != len(run.seasons):
            raise ValueError(
                f"Experiment {name!r} does not cover every research season."
            )

        score_deltas = [
            candidate[season].selection_score
            - baseline[season].selection_score
            for season in seasons
        ]
        interval_low, interval_high = bootstrap_mean_interval(
            score_deltas,
            samples=bootstrap_samples,
            confidence_level=confidence_level,
            random_seed=random_seed,
        )

        wins = sum(delta < -tie_tolerance for delta in score_deltas)
        losses = sum(delta > tie_tolerance for delta in score_deltas)
        ties = len(score_deltas) - wins - losses

        analyses.append(
            CandidateStatistics(
                name=name,
                seasons=len(seasons),
                wins=wins,
                losses=losses,
                ties=ties,
                mean_score_delta=fmean(score_deltas),
                median_score_delta=median(score_deltas),
                score_delta_stddev=(
                    stdev(score_deltas)
                    if len(score_deltas) > 1
                    else 0.0
                ),
                confidence_interval_low=interval_low,
                confidence_interval_high=interval_high,
                mean_accuracy_delta=fmean(
                    candidate[season].winner_accuracy
                    - baseline[season].winner_accuracy
                    for season in seasons
                ),
                mean_brier_delta=fmean(
                    candidate[season].brier_score
                    - baseline[season].brier_score
                    for season in seasons
                ),
                mean_log_loss_delta=fmean(
                    candidate[season].log_loss
                    - baseline[season].log_loss
                    for season in seasons
                ),
                mean_margin_mae_delta=fmean(
                    candidate[season].margin_mae
                    - baseline[season].margin_mae
                    for season in seasons
                ),
                mean_margin_rmse_delta=fmean(
                    candidate[season].margin_rmse
                    - baseline[season].margin_rmse
                    for season in seasons
                ),
            )
        )

    return tuple(
        sorted(
            analyses,
            key=lambda item: (
                item.mean_score_delta,
                -item.mean_accuracy_delta,
                item.name,
            ),
        )
    )


def bootstrap_mean_interval(
    values: list[float],
    *,
    samples: int,
    confidence_level: float,
    random_seed: int,
) -> tuple[float, float]:
    """Return a deterministic percentile bootstrap interval."""
    if not values:
        raise ValueError("Bootstrap requires at least one value.")

    random = Random(random_seed)
    count = len(values)
    means = sorted(
        fmean(values[random.randrange(count)] for _ in range(count))
        for _ in range(samples)
    )
    tail = (1.0 - confidence_level) / 2.0
    low_index = int(tail * (samples - 1))
    high_index = int((1.0 - tail) * (samples - 1))
    return means[low_index], means[high_index]
