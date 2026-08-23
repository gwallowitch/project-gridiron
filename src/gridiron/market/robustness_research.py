"""Robustness research for market-relative Project Gridiron signals."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gridiron.market.feature_residual_research import (
    NFLFeatureResidualObservation,
)
from gridiron.market.residual_research import (
    NFLMarketResidualMetrics,
    evaluate_probability_predictions,
    fit_logistic_probability_model,
)


@dataclass(frozen=True, slots=True)
class NFLChronologicalResidualFoldResult:
    """One chronological held-out block for a market-residual feature."""

    train_games: int
    test_games: int
    start_game_id: str
    end_game_id: str
    market_only: NFLMarketResidualMetrics
    market_plus_feature: NFLMarketResidualMetrics
    market_coefficient: float
    feature_coefficient: float
    combined_intercept: float


def run_expanding_window_feature_research(
    observations: tuple[NFLFeatureResidualObservation, ...],
    *,
    minimum_train_games: int = 300,
    test_block_games: int = 100,
) -> tuple[NFLChronologicalResidualFoldResult, ...]:
    """Evaluate one residual feature with chronological expanding windows."""
    if minimum_train_games < 1:
        raise ValueError("minimum_train_games must be positive.")

    if test_block_games < 1:
        raise ValueError("test_block_games must be positive.")

    ordered = tuple(
        sorted(
            observations,
            key=lambda observation: (
                observation.season,
                observation.game_id,
            ),
        )
    )

    if len(ordered) <= minimum_train_games:
        raise ValueError(
            "Not enough observations for the requested chronological split."
        )

    results: list[NFLChronologicalResidualFoldResult] = []

    test_start = minimum_train_games

    while test_start < len(ordered):
        test_end = min(
            test_start + test_block_games,
            len(ordered),
        )

        train = ordered[:test_start]
        test = ordered[test_start:test_end]

        if not test:
            break

        train_outcomes = np.array(
            [observation.home_win for observation in train],
            dtype=int,
        )
        test_outcomes = np.array(
            [observation.home_win for observation in test],
            dtype=int,
        )

        market_train = np.array(
            [
                [observation.market_home_probability]
                for observation in train
            ],
            dtype=float,
        )

        market_test = np.array(
            [
                [observation.market_home_probability]
                for observation in test
            ],
            dtype=float,
        )

        combined_train = np.array(
            [
                [
                    observation.market_home_probability,
                    observation.feature_value,
                ]
                for observation in train
            ],
            dtype=float,
        )

        combined_test = np.array(
            [
                [
                    observation.market_home_probability,
                    observation.feature_value,
                ]
                for observation in test
            ],
            dtype=float,
        )

        market_probabilities, _, _ = fit_logistic_probability_model(
            train_features=market_train,
            train_outcomes=train_outcomes,
            test_features=market_test,
        )

        combined_probabilities, coefficients, intercept = (
            fit_logistic_probability_model(
                train_features=combined_train,
                train_outcomes=train_outcomes,
                test_features=combined_test,
            )
        )

        results.append(
            NFLChronologicalResidualFoldResult(
                train_games=len(train),
                test_games=len(test),
                start_game_id=test[0].game_id,
                end_game_id=test[-1].game_id,
                market_only=evaluate_probability_predictions(
                    season=test[0].season,
                    model_name="market_only",
                    outcomes=test_outcomes,
                    probabilities=market_probabilities,
                ),
                market_plus_feature=evaluate_probability_predictions(
                    season=test[0].season,
                    model_name="market_plus_feature",
                    outcomes=test_outcomes,
                    probabilities=combined_probabilities,
                ),
                market_coefficient=float(coefficients[0]),
                feature_coefficient=float(coefficients[1]),
                combined_intercept=intercept,
            )
        )

        test_start = test_end

    return tuple(results)


@dataclass(frozen=True, slots=True)
class NFLResidualSliceMetrics:
    """Probability-quality deltas for one robustness slice."""

    label: str
    games: int
    brier_delta: float
    log_loss_delta: float


def summarize_probability_slice(
    *,
    label: str,
    outcomes: np.ndarray,
    market_probabilities: np.ndarray,
    candidate_probabilities: np.ndarray,
) -> NFLResidualSliceMetrics:
    """Compare candidate probabilities with the market baseline for one slice."""
    if len(outcomes) == 0:
        raise ValueError("Slice must contain at least one observation.")

    market_brier = float(
        np.mean((market_probabilities - outcomes) ** 2)
    )
    candidate_brier = float(
        np.mean((candidate_probabilities - outcomes) ** 2)
    )

    epsilon = 1e-15

    market_log_loss = float(
        -np.mean(
            outcomes
            * np.log(
                np.clip(
                    market_probabilities,
                    epsilon,
                    1.0 - epsilon,
                )
            )
            + (1.0 - outcomes)
            * np.log(
                np.clip(
                    1.0 - market_probabilities,
                    epsilon,
                    1.0 - epsilon,
                )
            )
        )
    )

    candidate_log_loss = float(
        -np.mean(
            outcomes
            * np.log(
                np.clip(
                    candidate_probabilities,
                    epsilon,
                    1.0 - epsilon,
                )
            )
            + (1.0 - outcomes)
            * np.log(
                np.clip(
                    1.0 - candidate_probabilities,
                    epsilon,
                    1.0 - epsilon,
                )
            )
        )
    )

    return NFLResidualSliceMetrics(
        label=label,
        games=len(outcomes),
        brier_delta=candidate_brier - market_brier,
        log_loss_delta=candidate_log_loss - market_log_loss,
    )


@dataclass(frozen=True, slots=True)
class NFLResidualAdjustmentSummary:
    """Summary of candidate probability movement relative to market."""

    label: str
    games: int
    mean_adjustment: float
    median_adjustment: float
    mean_absolute_adjustment: float
    p25_absolute_adjustment: float
    p75_absolute_adjustment: float
    p90_absolute_adjustment: float
    brier_delta: float
    log_loss_delta: float


def summarize_residual_adjustments(
    *,
    label: str,
    outcomes: np.ndarray,
    market_probabilities: np.ndarray,
    candidate_probabilities: np.ndarray,
) -> NFLResidualAdjustmentSummary:
    """Summarize residual probability movement and realized scoring impact."""
    if len(outcomes) == 0:
        raise ValueError("Adjustment summary requires at least one observation.")

    adjustments = candidate_probabilities - market_probabilities
    absolute_adjustments = np.abs(adjustments)

    slice_metrics = summarize_probability_slice(
        label=label,
        outcomes=outcomes,
        market_probabilities=market_probabilities,
        candidate_probabilities=candidate_probabilities,
    )

    return NFLResidualAdjustmentSummary(
        label=label,
        games=len(outcomes),
        mean_adjustment=float(np.mean(adjustments)),
        median_adjustment=float(np.median(adjustments)),
        mean_absolute_adjustment=float(np.mean(absolute_adjustments)),
        p25_absolute_adjustment=float(
            np.percentile(absolute_adjustments, 25)
        ),
        p75_absolute_adjustment=float(
            np.percentile(absolute_adjustments, 75)
        ),
        p90_absolute_adjustment=float(
            np.percentile(absolute_adjustments, 90)
        ),
        brier_delta=slice_metrics.brier_delta,
        log_loss_delta=slice_metrics.log_loss_delta,
    )


@dataclass(frozen=True, slots=True)
class NFLCappedResidualMetrics:
    """Held-out scoring metrics for one residual-adjustment cap."""

    cap: float | None
    games: int
    brier_score: float
    log_loss: float


def apply_residual_cap(
    *,
    market_probabilities: np.ndarray,
    candidate_probabilities: np.ndarray,
    cap: float | None,
) -> np.ndarray:
    """Cap candidate probability movement relative to the market baseline."""
    if cap is None:
        return candidate_probabilities.copy()

    if cap <= 0.0:
        raise ValueError("cap must be positive.")

    adjustment = candidate_probabilities - market_probabilities

    capped_adjustment = np.clip(
        adjustment,
        -cap,
        cap,
    )

    return np.clip(
        market_probabilities + capped_adjustment,
        0.0,
        1.0,
    )


def evaluate_capped_residual_probabilities(
    *,
    outcomes: np.ndarray,
    market_probabilities: np.ndarray,
    candidate_probabilities: np.ndarray,
    caps: tuple[float | None, ...],
) -> tuple[NFLCappedResidualMetrics, ...]:
    """Evaluate residual-probability caps against held-out outcomes."""
    results: list[NFLCappedResidualMetrics] = []

    for cap in caps:
        probabilities = apply_residual_cap(
            market_probabilities=market_probabilities,
            candidate_probabilities=candidate_probabilities,
            cap=cap,
        )

        metrics = evaluate_probability_predictions(
            season=0,
            model_name="capped_residual",
            outcomes=outcomes,
            probabilities=probabilities,
        )

        results.append(
            NFLCappedResidualMetrics(
                cap=cap,
                games=metrics.games,
                brier_score=metrics.brier_score,
                log_loss=metrics.log_loss,
            )
        )

    return tuple(results)


@dataclass(frozen=True, slots=True)
class NFLCapSelectionSummary:
    """Cross-season robustness summary for one residual cap."""

    cap: float
    seasons: int
    mean_brier_improvement: float
    worst_brier_improvement: float
    mean_log_loss_improvement: float
    worst_log_loss_improvement: float


def summarize_cap_robustness(
    *,
    cap: float,
    season_metrics: tuple[NFLCappedResidualMetrics, ...],
    market_metrics: tuple[NFLCappedResidualMetrics, ...],
) -> NFLCapSelectionSummary:
    """Summarize held-out improvement for one cap across seasons."""
    if len(season_metrics) != len(market_metrics):
        raise ValueError("Cap and market metric populations must match.")

    if not season_metrics:
        raise ValueError("At least one season is required.")

    brier_improvements = np.array(
        [
            market.brier_score - candidate.brier_score
            for candidate, market in zip(
                season_metrics,
                market_metrics,
                strict=True,
            )
        ],
        dtype=float,
    )

    log_loss_improvements = np.array(
        [
            market.log_loss - candidate.log_loss
            for candidate, market in zip(
                season_metrics,
                market_metrics,
                strict=True,
            )
        ],
        dtype=float,
    )

    return NFLCapSelectionSummary(
        cap=cap,
        seasons=len(season_metrics),
        mean_brier_improvement=float(np.mean(brier_improvements)),
        worst_brier_improvement=float(np.min(brier_improvements)),
        mean_log_loss_improvement=float(np.mean(log_loss_improvements)),
        worst_log_loss_improvement=float(np.min(log_loss_improvements)),
    )


def select_robust_residual_cap(
    summaries: tuple[NFLCapSelectionSummary, ...],
) -> NFLCapSelectionSummary:
    """Select cap using conservative worst-season Brier improvement."""
    if not summaries:
        raise ValueError("At least one cap summary is required.")

    return max(
        summaries,
        key=lambda summary: (
            summary.worst_brier_improvement,
            summary.worst_log_loss_improvement,
            summary.mean_brier_improvement,
            summary.mean_log_loss_improvement,
            -summary.cap,
        ),
    )
