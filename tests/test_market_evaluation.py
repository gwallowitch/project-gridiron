from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from gridiron.market.evaluation import (
    NFLMoneylineGameEvaluation,
    evaluate_moneyline_game,
)
from gridiron.market.moneyline import NFLMoneylineSnapshot


def _snapshot() -> NFLMoneylineSnapshot:
    return NFLMoneylineSnapshot(
        game_id="2026_01_BUF_NYJ",
        home_team_id="NYJ",
        away_team_id="BUF",
        provider="example-provider",
        observed_timestamp=datetime(2026, 9, 1, 12, tzinfo=UTC),
        home_american_odds=120,
        away_american_odds=-140,
    )


def test_evaluate_moneyline_game_composes_edge_and_expected_value() -> None:
    result = evaluate_moneyline_game(
        _snapshot(),
        home_calibrated_model_probability=0.48,
        away_calibrated_model_probability=0.52,
    )

    assert isinstance(result, NFLMoneylineGameEvaluation)

    assert result.edge.game_id == "2026_01_BUF_NYJ"
    assert result.edge.home_calibrated_model_probability == pytest.approx(0.48)
    assert result.edge.away_calibrated_model_probability == pytest.approx(0.52)

    assert result.home_expected_value.american_odds == 120
    assert result.away_expected_value.american_odds == -140

    assert result.home_expected_value.calibrated_model_probability == pytest.approx(
        0.48
    )
    assert result.away_expected_value.calibrated_model_probability == pytest.approx(
        0.52
    )


def test_evaluation_preserves_consistent_probabilities_across_components() -> None:
    result = evaluate_moneyline_game(
        _snapshot(),
        home_calibrated_model_probability=0.48,
        away_calibrated_model_probability=0.52,
    )

    assert (
        result.edge.home_calibrated_model_probability
        == result.home_expected_value.calibrated_model_probability
    )
    assert (
        result.edge.away_calibrated_model_probability
        == result.away_expected_value.calibrated_model_probability
    )


def test_evaluation_expected_values_use_offered_prices() -> None:
    result = evaluate_moneyline_game(
        _snapshot(),
        home_calibrated_model_probability=0.48,
        away_calibrated_model_probability=0.52,
    )

    assert result.home_expected_value.profit_per_unit_stake == pytest.approx(1.2)
    assert result.away_expected_value.profit_per_unit_stake == pytest.approx(
        100 / 140
    )


def test_evaluation_edges_are_complements() -> None:
    result = evaluate_moneyline_game(
        _snapshot(),
        home_calibrated_model_probability=0.48,
        away_calibrated_model_probability=0.52,
    )

    assert result.edge.home_edge + result.edge.away_edge == pytest.approx(0.0)


def test_evaluation_is_immutable() -> None:
    result = evaluate_moneyline_game(
        _snapshot(),
        home_calibrated_model_probability=0.48,
        away_calibrated_model_probability=0.52,
    )

    with pytest.raises(FrozenInstanceError):
        result.edge = result.edge  # type: ignore[misc]


def test_invalid_probabilities_propagate_from_edge_validation() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        evaluate_moneyline_game(
            _snapshot(),
            home_calibrated_model_probability=0.60,
            away_calibrated_model_probability=0.45,
        )
