"""Pure functions for market-price calculations.

The module deliberately contains no sportsbook, team, or recommendation logic.
Keeping the mathematics pure makes historical testing reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class TwoWayFairMarket:
    """Normalized probabilities for mutually exclusive two-way outcomes."""

    first: float
    second: float
    overround: float


def american_to_decimal(american_odds: int) -> float:
    """Convert American odds to decimal odds."""
    if american_odds == 0:
        raise ValueError("American odds cannot be zero.")
    if american_odds > 0:
        return 1.0 + american_odds / 100.0
    return 1.0 + 100.0 / abs(american_odds)


def decimal_to_implied_probability(decimal_odds: float) -> float:
    """Return the break-even probability implied by decimal odds."""
    if not isfinite(decimal_odds) or decimal_odds <= 1.0:
        raise ValueError("Decimal odds must be finite and greater than 1.0.")
    return 1.0 / decimal_odds


def american_to_implied_probability(american_odds: int) -> float:
    """Return the break-even probability implied by American odds."""
    return decimal_to_implied_probability(american_to_decimal(american_odds))


def remove_two_way_margin(first_odds: int, second_odds: int) -> TwoWayFairMarket:
    """Remove a two-way market margin using proportional normalization."""
    first_raw = american_to_implied_probability(first_odds)
    second_raw = american_to_implied_probability(second_odds)
    raw_total = first_raw + second_raw
    if raw_total <= 0.0:
        raise ValueError("The market's implied probability total must be positive.")
    return TwoWayFairMarket(
        first=first_raw / raw_total,
        second=second_raw / raw_total,
        overround=raw_total - 1.0,
    )


def expected_profit_per_unit(win_probability: float, american_odds: int) -> float:
    """Return expected profit for one unit risked, before tax or limits."""
    _validate_probability(win_probability)
    profit_if_win = american_to_decimal(american_odds) - 1.0
    loss_probability = 1.0 - win_probability
    return win_probability * profit_if_win - loss_probability


def fractional_kelly(
    win_probability: float,
    american_odds: int,
    *,
    fraction: float = 0.25,
    cap: float = 0.01,
) -> float:
    """Return a nonnegative, capped fraction of bankroll.

    A result of zero means the supplied probability has no mathematical edge.
    The conservative defaults are risk controls, not a recommendation.
    """
    _validate_probability(win_probability)
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("Kelly fraction must be between 0 and 1.")
    if not 0.0 <= cap <= 1.0:
        raise ValueError("Bankroll cap must be between 0 and 1.")

    net_decimal = american_to_decimal(american_odds) - 1.0
    loss_probability = 1.0 - win_probability
    full_kelly = (net_decimal * win_probability - loss_probability) / net_decimal
    return min(max(full_kelly * fraction, 0.0), cap)


def _validate_probability(probability: float) -> None:
    if not isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError("Probability must be finite and between 0 and 1.")

