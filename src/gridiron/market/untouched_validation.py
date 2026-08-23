"""Untouched validation for the frozen Step 90E residual candidate."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gridiron.market.residual_research import (
    NFLMarketResidualMetrics,
    evaluate_probability_predictions,
    fit_logistic_probability_model,
)
from gridiron.market.robustness_research import (
    apply_residual_cap,
)

FROZEN_RESIDUAL_CAP = 0.0425


@dataclass(frozen=True, slots=True)
class NFLUntouchedValidationResult:
    """Frozen candidate versus market-only on one untouched population."""

    games: int
    market_only: NFLMarketResidualMetrics
    capped_residual: NFLMarketResidualMetrics
    market_coefficient: float
    def_epa_coefficient: float
    intercept: float


def run_frozen_untouched_validation(
    *,
    train_market_probabilities: np.ndarray,
    train_def_epa: np.ndarray,
    train_outcomes: np.ndarray,
    test_market_probabilities: np.ndarray,
    test_def_epa: np.ndarray,
    test_outcomes: np.ndarray,
) -> NFLUntouchedValidationResult:
    """Run the frozen 4.25% DEF EPA residual candidate without tuning."""
    if len(test_outcomes) == 0:
        raise ValueError("Untouched validation requires test observations.")

    if not (
        len(train_market_probabilities)
        == len(train_def_epa)
        == len(train_outcomes)
    ):
        raise ValueError("Training population lengths must match.")

    if not (
        len(test_market_probabilities)
        == len(test_def_epa)
        == len(test_outcomes)
    ):
        raise ValueError("Test population lengths must match.")

    market_train = np.asarray(
        train_market_probabilities,
        dtype=float,
    ).reshape(-1, 1)

    combined_train = np.column_stack(
        (
            np.asarray(
                train_market_probabilities,
                dtype=float,
            ),
            np.asarray(
                train_def_epa,
                dtype=float,
            ),
        )
    )

    market_test = np.asarray(
        test_market_probabilities,
        dtype=float,
    ).reshape(-1, 1)

    combined_test = np.column_stack(
        (
            np.asarray(
                test_market_probabilities,
                dtype=float,
            ),
            np.asarray(
                test_def_epa,
                dtype=float,
            ),
        )
    )

    market_probabilities, _, _ = fit_logistic_probability_model(
        train_features=market_train,
        train_outcomes=np.asarray(
            train_outcomes,
            dtype=int,
        ),
        test_features=market_test,
    )

    candidate_probabilities, coefficients, intercept = (
        fit_logistic_probability_model(
            train_features=combined_train,
            train_outcomes=np.asarray(
                train_outcomes,
                dtype=int,
            ),
            test_features=combined_test,
        )
    )

    capped_probabilities = apply_residual_cap(
        market_probabilities=market_probabilities,
        candidate_probabilities=candidate_probabilities,
        cap=FROZEN_RESIDUAL_CAP,
    )

    market_metrics = evaluate_probability_predictions(
        season=2025,
        model_name="market_only",
        outcomes=np.asarray(
            test_outcomes,
            dtype=int,
        ),
        probabilities=market_probabilities,
    )

    capped_metrics = evaluate_probability_predictions(
        season=2025,
        model_name="market_plus_def_epa_capped",
        outcomes=np.asarray(
            test_outcomes,
            dtype=int,
        ),
        probabilities=capped_probabilities,
    )

    return NFLUntouchedValidationResult(
        games=len(test_outcomes),
        market_only=market_metrics,
        capped_residual=capped_metrics,
        market_coefficient=float(coefficients[0]),
        def_epa_coefficient=float(coefficients[1]),
        intercept=float(intercept),
    )
