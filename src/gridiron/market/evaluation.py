"""Combined NFL moneyline model-versus-market evaluation records."""

from __future__ import annotations

from dataclasses import dataclass

from gridiron.market.edge import NFLMoneylineEdge, calculate_moneyline_edge
from gridiron.market.expected_value import (
    NFLMoneylineExpectedValue,
    calculate_moneyline_expected_value,
)
from gridiron.market.moneyline import NFLMoneylineSnapshot


@dataclass(frozen=True, slots=True)
class NFLMoneylineGameEvaluation:
    """Immutable model, market, edge, and expected-value evaluation."""

    edge: NFLMoneylineEdge
    home_expected_value: NFLMoneylineExpectedValue
    away_expected_value: NFLMoneylineExpectedValue


def evaluate_moneyline_game(
    snapshot: NFLMoneylineSnapshot,
    *,
    home_calibrated_model_probability: float,
    away_calibrated_model_probability: float,
) -> NFLMoneylineGameEvaluation:
    """Build a complete per-game moneyline evaluation without bet selection."""
    edge = calculate_moneyline_edge(
        snapshot,
        home_calibrated_model_probability=home_calibrated_model_probability,
        away_calibrated_model_probability=away_calibrated_model_probability,
    )

    home_expected_value = calculate_moneyline_expected_value(
        american_odds=snapshot.home_american_odds,
        calibrated_model_probability=home_calibrated_model_probability,
    )
    away_expected_value = calculate_moneyline_expected_value(
        american_odds=snapshot.away_american_odds,
        calibrated_model_probability=away_calibrated_model_probability,
    )

    return NFLMoneylineGameEvaluation(
        edge=edge,
        home_expected_value=home_expected_value,
        away_expected_value=away_expected_value,
    )
