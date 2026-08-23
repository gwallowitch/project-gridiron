"""Feature-level market-residual research for Project Gridiron."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from gridiron.market.residual_research import (
    NFLMarketResidualMetrics,
    evaluate_probability_predictions,
    fit_logistic_probability_model,
)


@dataclass(frozen=True, slots=True)
class NFLFeatureResidualObservation:
    """One settled game with market probability and one football feature."""

    season: int
    game_id: str
    market_home_probability: float
    feature_value: float
    home_win: int


@dataclass(frozen=True, slots=True)
class NFLFeatureResidualFoldResult:
    """Held-out comparison of market-only and market-plus-feature models."""

    feature_name: str
    test_season: int
    market_only: NFLMarketResidualMetrics
    market_plus_feature: NFLMarketResidualMetrics
    market_coefficient: float
    feature_coefficient: float
    combined_intercept: float


def attach_feature_to_market_observations(
    *,
    market_frame: pl.DataFrame,
    feature_path: Path,
    feature_column: str,
) -> tuple[NFLFeatureResidualObservation, ...]:
    """Attach one historical football feature using production-style zero fill."""
    features = pl.read_parquet(feature_path).select(
        "game_id",
        pl.col(feature_column).alias("feature_value"),
    )

    joined = (
        market_frame.join(
            features,
            on="game_id",
            how="left",
        )
        .with_columns(
            pl.col("feature_value")
            .fill_nan(0.0)
            .fill_null(0.0)
        )
    )

    if joined.height != market_frame.height:
        raise ValueError(
            "Feature join changed the historical market population: "
            f"{market_frame.height} -> {joined.height}"
        )

    return tuple(
        NFLFeatureResidualObservation(
            season=int(row["season"]),
            game_id=str(row["game_id"]),
            market_home_probability=float(row["market_home_probability"]),
            feature_value=float(row["feature_value"]),
            home_win=int(row["home_win"]),
        )
        for row in joined.iter_rows(named=True)
    )


def run_leave_one_season_out_feature_residual_research(
    *,
    feature_name: str,
    observations: tuple[NFLFeatureResidualObservation, ...],
) -> tuple[NFLFeatureResidualFoldResult, ...]:
    """Test whether one football feature adds signal beyond the market."""
    seasons = tuple(
        sorted({observation.season for observation in observations})
    )
    results: list[NFLFeatureResidualFoldResult] = []

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
            NFLFeatureResidualFoldResult(
                feature_name=feature_name,
                test_season=test_season,
                market_only=evaluate_probability_predictions(
                    season=test_season,
                    model_name="market_only",
                    outcomes=test_outcomes,
                    probabilities=market_probabilities,
                ),
                market_plus_feature=evaluate_probability_predictions(
                    season=test_season,
                    model_name=f"market_plus_{feature_name}",
                    outcomes=test_outcomes,
                    probabilities=combined_probabilities,
                ),
                market_coefficient=float(coefficients[0]),
                feature_coefficient=float(coefficients[1]),
                combined_intercept=intercept,
            )
        )

    return tuple(results)


@dataclass(frozen=True, slots=True)
class NFLTwoFeatureResidualObservation:
    """One settled game with market probability and two football features."""

    season: int
    game_id: str
    market_home_probability: float
    first_feature_value: float
    second_feature_value: float
    home_win: int


@dataclass(frozen=True, slots=True)
class NFLTwoFeatureResidualFoldResult:
    """Held-out comparison for market plus two candidate residual features."""

    test_season: int
    market_only: NFLMarketResidualMetrics
    market_plus_first: NFLMarketResidualMetrics
    market_plus_second: NFLMarketResidualMetrics
    market_plus_both: NFLMarketResidualMetrics
    both_coefficients: tuple[float, float, float]
    both_intercept: float


def run_leave_one_season_out_two_feature_research(
    observations: tuple[NFLTwoFeatureResidualObservation, ...],
) -> tuple[NFLTwoFeatureResidualFoldResult, ...]:
    """Evaluate two residual features individually and together."""
    seasons = tuple(sorted({observation.season for observation in observations}))
    results: list[NFLTwoFeatureResidualFoldResult] = []

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

        first_train = np.array(
            [
                [
                    observation.market_home_probability,
                    observation.first_feature_value,
                ]
                for observation in train
            ],
            dtype=float,
        )
        first_test = np.array(
            [
                [
                    observation.market_home_probability,
                    observation.first_feature_value,
                ]
                for observation in test
            ],
            dtype=float,
        )

        second_train = np.array(
            [
                [
                    observation.market_home_probability,
                    observation.second_feature_value,
                ]
                for observation in train
            ],
            dtype=float,
        )
        second_test = np.array(
            [
                [
                    observation.market_home_probability,
                    observation.second_feature_value,
                ]
                for observation in test
            ],
            dtype=float,
        )

        both_train = np.array(
            [
                [
                    observation.market_home_probability,
                    observation.first_feature_value,
                    observation.second_feature_value,
                ]
                for observation in train
            ],
            dtype=float,
        )
        both_test = np.array(
            [
                [
                    observation.market_home_probability,
                    observation.first_feature_value,
                    observation.second_feature_value,
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

        first_probabilities, _, _ = fit_logistic_probability_model(
            train_features=first_train,
            train_outcomes=train_outcomes,
            test_features=first_test,
        )

        second_probabilities, _, _ = fit_logistic_probability_model(
            train_features=second_train,
            train_outcomes=train_outcomes,
            test_features=second_test,
        )

        both_probabilities, coefficients, intercept = (
            fit_logistic_probability_model(
                train_features=both_train,
                train_outcomes=train_outcomes,
                test_features=both_test,
            )
        )

        results.append(
            NFLTwoFeatureResidualFoldResult(
                test_season=test_season,
                market_only=evaluate_probability_predictions(
                    season=test_season,
                    model_name="market_only",
                    outcomes=test_outcomes,
                    probabilities=market_probabilities,
                ),
                market_plus_first=evaluate_probability_predictions(
                    season=test_season,
                    model_name="market_plus_def_epa_trend",
                    outcomes=test_outcomes,
                    probabilities=first_probabilities,
                ),
                market_plus_second=evaluate_probability_predictions(
                    season=test_season,
                    model_name="market_plus_def_schedule",
                    outcomes=test_outcomes,
                    probabilities=second_probabilities,
                ),
                market_plus_both=evaluate_probability_predictions(
                    season=test_season,
                    model_name="market_plus_both",
                    outcomes=test_outcomes,
                    probabilities=both_probabilities,
                ),
                both_coefficients=(
                    float(coefficients[0]),
                    float(coefficients[1]),
                    float(coefficients[2]),
                ),
                both_intercept=intercept,
            )
        )

    return tuple(results)
