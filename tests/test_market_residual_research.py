from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from gridiron.market.historical import NFLHistoricalMoneylineRecord
from gridiron.market.residual_research import (
    build_market_residual_observations,
    evaluate_probability_predictions,
    fit_logistic_probability_model,
)


def _record(
    *,
    season: int = 2024,
    game_id: str = "2024_01_AWAY_HOME",
    home_probability: float = 0.60,
    away_probability: float = 0.40,
    winning_team_id: str = "HOME",
    home_odds: int = -120,
    away_odds: int = 110,
) -> NFLHistoricalMoneylineRecord:
    return NFLHistoricalMoneylineRecord(
        season=season,
        week=1,
        game_id=game_id,
        home_team_id="HOME",
        away_team_id="AWAY",
        provider="historical-dataset",
        observed_timestamp=datetime(2024, 9, 1, 12, tzinfo=UTC),
        home_american_odds=home_odds,
        away_american_odds=away_odds,
        home_calibrated_model_probability=home_probability,
        away_calibrated_model_probability=away_probability,
        winning_team_id=winning_team_id,
    )


def test_build_market_residual_observation() -> None:
    observations = build_market_residual_observations((_record(),))

    assert len(observations) == 1

    observation = observations[0]
    assert observation.season == 2024
    assert observation.game_id == "2024_01_AWAY_HOME"
    assert observation.gridiron_home_probability == pytest.approx(0.60)
    assert 0.0 < observation.market_home_probability < 1.0
    assert observation.home_win == 1


def test_build_market_residual_observation_for_away_win() -> None:
    observation = build_market_residual_observations(
        (_record(winning_team_id="AWAY"),)
    )[0]

    assert observation.home_win == 0


def test_probability_metrics_are_calculated() -> None:
    outcomes = np.array([1, 0, 1, 0], dtype=int)
    probabilities = np.array([0.8, 0.3, 0.6, 0.2], dtype=float)

    metrics = evaluate_probability_predictions(
        season=2024,
        model_name="example",
        outcomes=outcomes,
        probabilities=probabilities,
    )

    assert metrics.games == 4
    assert metrics.accuracy == pytest.approx(1.0)
    assert 0.0 < metrics.brier_score < 1.0
    assert metrics.log_loss > 0.0


def test_logistic_model_is_deterministic() -> None:
    train_features = np.array(
        [
            [0.1],
            [0.2],
            [0.3],
            [0.7],
            [0.8],
            [0.9],
        ],
        dtype=float,
    )
    train_outcomes = np.array([0, 0, 0, 1, 1, 1], dtype=int)
    test_features = np.array([[0.25], [0.75]], dtype=float)

    first = fit_logistic_probability_model(
        train_features=train_features,
        train_outcomes=train_outcomes,
        test_features=test_features,
    )
    second = fit_logistic_probability_model(
        train_features=train_features,
        train_outcomes=train_outcomes,
        test_features=test_features,
    )

    assert np.allclose(first[0], second[0])
    assert np.allclose(first[1], second[1])
    assert first[2] == pytest.approx(second[2])


def test_logistic_model_returns_probability_bounds() -> None:
    train_features = np.array(
        [
            [0.1],
            [0.2],
            [0.3],
            [0.7],
            [0.8],
            [0.9],
        ],
        dtype=float,
    )
    train_outcomes = np.array([0, 0, 0, 1, 1, 1], dtype=int)
    test_features = np.array([[0.25], [0.75]], dtype=float)

    probabilities, coefficients, intercept = fit_logistic_probability_model(
        train_features=train_features,
        train_outcomes=train_outcomes,
        test_features=test_features,
    )

    assert probabilities.shape == (2,)
    assert coefficients.shape == (1,)
    assert np.all(probabilities > 0.0)
    assert np.all(probabilities < 1.0)
    assert np.isfinite(intercept)

from gridiron.market.residual_research import (
    NFLMarketResidualObservation,
    run_leave_one_season_out_residual_research,
)


def test_leave_one_season_out_returns_one_fold_per_season() -> None:
    observations = (
        NFLMarketResidualObservation(2022, "a", 0.70, 0.60, 1),
        NFLMarketResidualObservation(2022, "b", 0.30, 0.40, 0),
        NFLMarketResidualObservation(2023, "c", 0.65, 0.55, 1),
        NFLMarketResidualObservation(2023, "d", 0.35, 0.45, 0),
        NFLMarketResidualObservation(2024, "e", 0.75, 0.65, 1),
        NFLMarketResidualObservation(2024, "f", 0.25, 0.35, 0),
    )

    results = run_leave_one_season_out_residual_research(observations)

    assert tuple(result.test_season for result in results) == (
        2022,
        2023,
        2024,
    )

    for result in results:
        assert result.market_only.games == 2
        assert result.gridiron_only.games == 2
        assert result.market_plus_gridiron.games == 2
        assert len(result.combined_coefficients) == 2
