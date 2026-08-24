"""Frozen 2025 economic evaluation for the Step 90E residual candidate."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gridiron.market.economic_research import (
    NFLEconomicObservation,
    fixed_absolute_adjustment_bucket,
    summarize_economic_bucket,
)
from gridiron.market.residual_research import (
    fit_logistic_probability_model,
)
from gridiron.market.robustness_research import apply_residual_cap
from gridiron.market.untouched_validation import (
    FROZEN_RESIDUAL_CAP,
)


@dataclass(frozen=True, slots=True)
class NFLFrozenEconomicGame:
    """One frozen-candidate game for economic evaluation."""

    game_id: str
    market_home_probability: float
    candidate_home_probability: float
    home_american_odds: int
    away_american_odds: int
    home_win: bool

    @property
    def residual_adjustment(self) -> float:
        return (
            self.candidate_home_probability
            - self.market_home_probability
        )

    @property
    def adjustment_bucket(self) -> str:
        return fixed_absolute_adjustment_bucket(
            self.residual_adjustment
        )

    def preferred_side(self) -> NFLEconomicObservation:
        """Return the side favored by the frozen residual adjustment."""
        if self.residual_adjustment >= 0.0:
            return NFLEconomicObservation(
                game_id=self.game_id,
                side="HOME",
                candidate_probability=self.candidate_home_probability,
                offered_american_odds=self.home_american_odds,
                won=self.home_win,
            )

        return NFLEconomicObservation(
            game_id=self.game_id,
            side="AWAY",
            candidate_probability=(
                1.0 - self.candidate_home_probability
            ),
            offered_american_odds=self.away_american_odds,
            won=not self.home_win,
        )


def build_frozen_candidate_probabilities(
    *,
    train_market_probabilities: np.ndarray,
    train_def_epa: np.ndarray,
    train_outcomes: np.ndarray,
    test_market_probabilities: np.ndarray,
    test_def_epa: np.ndarray,
) -> np.ndarray:
    """Fit the frozen residual model and return capped test probabilities."""
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

    candidate_probabilities, _, _ = (
        fit_logistic_probability_model(
            train_features=combined_train,
            train_outcomes=np.asarray(
                train_outcomes,
                dtype=int,
            ),
            test_features=combined_test,
        )
    )

    market_train = np.asarray(
        train_market_probabilities,
        dtype=float,
    ).reshape(-1, 1)

    market_test = np.asarray(
        test_market_probabilities,
        dtype=float,
    ).reshape(-1, 1)

    market_probabilities, _, _ = (
        fit_logistic_probability_model(
            train_features=market_train,
            train_outcomes=np.asarray(
                train_outcomes,
                dtype=int,
            ),
            test_features=market_test,
        )
    )

    return apply_residual_cap(
        market_probabilities=market_probabilities,
        candidate_probabilities=candidate_probabilities,
        cap=FROZEN_RESIDUAL_CAP,
    )


def summarize_frozen_economic_buckets(
    games: tuple[NFLFrozenEconomicGame, ...],
) -> tuple:
    """Summarize fixed residual-movement buckets descriptively."""
    labels = (
        "<1%",
        "1-2%",
        "2-3%",
        "3-4.25%",
    )

    results = []

    for label in labels:
        observations = tuple(
            game.preferred_side()
            for game in games
            if game.adjustment_bucket == label
        )

        if not observations:
            continue

        results.append(
            summarize_economic_bucket(
                label=label,
                observations=observations,
            )
        )

    return tuple(results)
