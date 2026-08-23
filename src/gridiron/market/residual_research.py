"""Market-relative residual research for Project Gridiron."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, mean_squared_error

from gridiron.market.historical import NFLHistoricalMoneylineRecord
from gridiron.market.moneyline import remove_two_sided_vig


@dataclass(frozen=True, slots=True)
class NFLMarketResidualObservation:
    """One settled game for market-relative probability research."""

    season: int
    game_id: str
    market_home_probability: float
    gridiron_home_probability: float
    home_win: int


@dataclass(frozen=True, slots=True)
class NFLMarketResidualMetrics:
    """Held-out metrics for one probability model."""

    season: int
    model_name: str
    games: int
    accuracy: float
    brier_score: float
    log_loss: float


def build_market_residual_observations(
    records: tuple[NFLHistoricalMoneylineRecord, ...],
) -> tuple[NFLMarketResidualObservation, ...]:
    """Convert historical moneyline records into residual-research observations."""
    observations: list[NFLMarketResidualObservation] = []

    for record in records:
        fair = remove_two_sided_vig(
            record.home_american_odds,
            record.away_american_odds,
        )

        observations.append(
            NFLMarketResidualObservation(
                season=record.season,
                game_id=record.game_id,
                market_home_probability=fair.home_fair_probability,
                gridiron_home_probability=(
                    record.home_calibrated_model_probability
                ),
                home_win=int(record.winning_team_id == record.home_team_id),
            )
        )

    return tuple(observations)


def evaluate_probability_predictions(
    *,
    season: int,
    model_name: str,
    outcomes: np.ndarray,
    probabilities: np.ndarray,
) -> NFLMarketResidualMetrics:
    """Evaluate held-out home-win probabilities."""
    predictions = (probabilities >= 0.5).astype(int)

    return NFLMarketResidualMetrics(
        season=season,
        model_name=model_name,
        games=len(outcomes),
        accuracy=float(np.mean(predictions == outcomes)),
        brier_score=float(mean_squared_error(outcomes, probabilities)),
        log_loss=float(log_loss(outcomes, probabilities, labels=[0, 1])),
    )


def fit_logistic_probability_model(
    *,
    train_features: np.ndarray,
    train_outcomes: np.ndarray,
    test_features: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Fit deterministic logistic regression and return probabilities and coefficients."""
    model = LogisticRegression(
        C=np.inf,
        solver="lbfgs",
        max_iter=1000,
        random_state=0,
    )
    model.fit(train_features, train_outcomes)

    probabilities = model.predict_proba(test_features)[:, 1]

    return (
        probabilities,
        model.coef_[0].copy(),
        float(model.intercept_[0]),
    )


@dataclass(frozen=True, slots=True)
class NFLMarketResidualFoldResult:
    """Held-out season comparison of market and Gridiron probability models."""

    test_season: int
    market_only: NFLMarketResidualMetrics
    gridiron_only: NFLMarketResidualMetrics
    market_plus_gridiron: NFLMarketResidualMetrics
    combined_coefficients: tuple[float, float]
    combined_intercept: float


def run_leave_one_season_out_residual_research(
    observations: tuple[NFLMarketResidualObservation, ...],
) -> tuple[NFLMarketResidualFoldResult, ...]:
    """Compare market-only, Gridiron-only, and combined models by held-out season."""
    seasons = tuple(sorted({observation.season for observation in observations}))
    results: list[NFLMarketResidualFoldResult] = []

    for test_season in seasons:
        train = tuple(
            observation
            for observation in observations
            if observation.season != test_season
        )
        test = tuple(
            observation
            for observation in observations
            if observation.season == test_season
        )

        train_outcomes = np.array(
            [observation.home_win for observation in train],
            dtype=int,
        )
        test_outcomes = np.array(
            [observation.home_win for observation in test],
            dtype=int,
        )

        market_train = np.array(
            [[observation.market_home_probability] for observation in train],
            dtype=float,
        )
        market_test = np.array(
            [[observation.market_home_probability] for observation in test],
            dtype=float,
        )

        gridiron_train = np.array(
            [[observation.gridiron_home_probability] for observation in train],
            dtype=float,
        )
        gridiron_test = np.array(
            [[observation.gridiron_home_probability] for observation in test],
            dtype=float,
        )

        combined_train = np.array(
            [
                [
                    observation.market_home_probability,
                    observation.gridiron_home_probability,
                ]
                for observation in train
            ],
            dtype=float,
        )
        combined_test = np.array(
            [
                [
                    observation.market_home_probability,
                    observation.gridiron_home_probability,
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

        gridiron_probabilities, _, _ = fit_logistic_probability_model(
            train_features=gridiron_train,
            train_outcomes=train_outcomes,
            test_features=gridiron_test,
        )

        (
            combined_probabilities,
            combined_coefficients,
            combined_intercept,
        ) = fit_logistic_probability_model(
            train_features=combined_train,
            train_outcomes=train_outcomes,
            test_features=combined_test,
        )

        results.append(
            NFLMarketResidualFoldResult(
                test_season=test_season,
                market_only=evaluate_probability_predictions(
                    season=test_season,
                    model_name="market_only",
                    outcomes=test_outcomes,
                    probabilities=market_probabilities,
                ),
                gridiron_only=evaluate_probability_predictions(
                    season=test_season,
                    model_name="gridiron_only",
                    outcomes=test_outcomes,
                    probabilities=gridiron_probabilities,
                ),
                market_plus_gridiron=evaluate_probability_predictions(
                    season=test_season,
                    model_name="market_plus_gridiron",
                    outcomes=test_outcomes,
                    probabilities=combined_probabilities,
                ),
                combined_coefficients=(
                    float(combined_coefficients[0]),
                    float(combined_coefficients[1]),
                ),
                combined_intercept=combined_intercept,
            )
        )

    return tuple(results)
