"""Expected-value calculations for NFL moneyline prices."""

from __future__ import annotations

import math
from dataclasses import dataclass

from gridiron.market.moneyline import american_odds_to_implied_probability


@dataclass(frozen=True, slots=True)
class NFLMoneylineExpectedValue:
    """Expected value for one side of an NFL moneyline at the offered price."""

    american_odds: int
    calibrated_model_probability: float
    market_implied_probability: float
    profit_per_unit_stake: float
    expected_profit_per_unit_stake: float
    expected_roi: float


def calculate_moneyline_expected_value(
    *,
    american_odds: int,
    calibrated_model_probability: float,
) -> NFLMoneylineExpectedValue:
    """Calculate unit-stake expected value using the offered American price."""
    _validate_probability(calibrated_model_probability)

    implied_probability = american_odds_to_implied_probability(american_odds)
    profit_per_unit_stake = _american_odds_profit_per_unit(american_odds)

    expected_profit = (
        calibrated_model_probability * profit_per_unit_stake
        - (1.0 - calibrated_model_probability)
    )

    return NFLMoneylineExpectedValue(
        american_odds=american_odds,
        calibrated_model_probability=calibrated_model_probability,
        market_implied_probability=implied_probability,
        profit_per_unit_stake=profit_per_unit_stake,
        expected_profit_per_unit_stake=expected_profit,
        expected_roi=expected_profit,
    )


def _american_odds_profit_per_unit(american_odds: int) -> float:
    american_odds_to_implied_probability(american_odds)

    if american_odds > 0:
        return american_odds / 100.0

    return 100.0 / abs(american_odds)


def _validate_probability(probability: float) -> None:
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        raise TypeError("calibrated_model_probability must be numeric.")

    numeric_probability = float(probability)
    if not math.isfinite(numeric_probability):
        raise ValueError("calibrated_model_probability must be finite.")

    if not 0.0 <= numeric_probability <= 1.0:
        raise ValueError("calibrated_model_probability must be between 0 and 1.")
