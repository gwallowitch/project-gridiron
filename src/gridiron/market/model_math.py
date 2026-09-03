"""Pure protocol-neutral market plus DEF EPA decision mathematics."""

from __future__ import annotations

import math
from dataclasses import dataclass

from gridiron.market.moneyline import american_odds_to_implied_probability


@dataclass(frozen=True, slots=True)
class CappedModelPosition:
    """Probability and side after applying the symmetric market residual cap."""

    raw_home_probability: float
    model_home_probability: float
    selected_side: str
    selected_probability: float


@dataclass(frozen=True, slots=True)
class MarketModelDecision:
    """Complete deterministic decision from already-resolved numeric inputs."""

    raw_home_probability: float
    model_home_probability: float
    selected_side: str
    selected_probability: float
    selected_odds: int | None
    break_even_probability: float | None
    edge: float | None
    is_bet: bool


def calculate_capped_model_position(
    market_home_probability: float,
    def_epa: float,
    *,
    market_coefficient: float,
    def_epa_coefficient: float,
    intercept: float,
    residual_cap: float,
) -> CappedModelPosition:
    """Apply the canonical logistic transform, cap, and side selection."""
    raw_home = 1.0 / (
        1.0
        + math.exp(
            -(
                intercept
                + market_coefficient * market_home_probability
                + def_epa_coefficient * def_epa
            )
        )
    )
    model_home = min(
        market_home_probability + residual_cap,
        max(market_home_probability - residual_cap, raw_home),
    )
    side = "HOME" if model_home >= market_home_probability else "AWAY"
    selected_probability = model_home if side == "HOME" else 1.0 - model_home
    return CappedModelPosition(
        raw_home,
        model_home,
        side,
        selected_probability,
    )


def calculate_edge_decision(
    position: CappedModelPosition,
    *,
    home_odds: int | None,
    away_odds: int | None,
) -> MarketModelDecision:
    """Apply canonical execution-price selection and strict-positive edge logic."""
    selected_odds = home_odds if position.selected_side == "HOME" else away_odds
    break_even = (
        None
        if selected_odds is None
        else american_odds_to_implied_probability(selected_odds)
    )
    edge = (
        None
        if break_even is None
        else position.selected_probability - break_even
    )
    is_bet = edge is not None and edge > 0.0
    return MarketModelDecision(
        position.raw_home_probability,
        position.model_home_probability,
        position.selected_side,
        position.selected_probability,
        selected_odds,
        break_even,
        edge,
        is_bet,
    )


def calculate_market_model_decision(
    market_home_probability: float,
    def_epa: float,
    *,
    home_odds: int | None,
    away_odds: int | None,
    market_coefficient: float,
    def_epa_coefficient: float,
    intercept: float,
    residual_cap: float,
) -> MarketModelDecision:
    """Return the canonical decision without protocol, filesystem, or clock state."""
    position = calculate_capped_model_position(
        market_home_probability,
        def_epa,
        market_coefficient=market_coefficient,
        def_epa_coefficient=def_epa_coefficient,
        intercept=intercept,
        residual_cap=residual_cap,
    )
    return calculate_edge_decision(
        position,
        home_odds=home_odds,
        away_odds=away_odds,
    )


__all__ = [
    "CappedModelPosition",
    "MarketModelDecision",
    "calculate_capped_model_position",
    "calculate_edge_decision",
    "calculate_market_model_decision",
]
