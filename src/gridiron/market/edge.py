"""Model-versus-market edge calculations for NFL moneylines."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from gridiron.market.moneyline import NFLMoneylineSnapshot, remove_two_sided_vig


@dataclass(frozen=True, slots=True)
class NFLMoneylineEdge:
    """Immutable calibrated-model versus vig-free market comparison."""

    game_id: str
    home_team_id: str
    away_team_id: str
    provider: str
    observed_timestamp: datetime

    home_american_odds: int
    away_american_odds: int

    home_market_implied_probability: float
    away_market_implied_probability: float
    home_market_fair_probability: float
    away_market_fair_probability: float

    home_calibrated_model_probability: float
    away_calibrated_model_probability: float

    home_edge: float
    away_edge: float


def calculate_moneyline_edge(
    snapshot: NFLMoneylineSnapshot,
    *,
    home_calibrated_model_probability: float,
    away_calibrated_model_probability: float,
) -> NFLMoneylineEdge:
    """Compare calibrated model probabilities with vig-free market probabilities."""
    _validate_probability(
        home_calibrated_model_probability,
        "home_calibrated_model_probability",
    )
    _validate_probability(
        away_calibrated_model_probability,
        "away_calibrated_model_probability",
    )

    probability_total = (
        home_calibrated_model_probability + away_calibrated_model_probability
    )
    if not math.isclose(probability_total, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("Calibrated home and away probabilities must sum to 1.0.")

    fair = remove_two_sided_vig(
        snapshot.home_american_odds,
        snapshot.away_american_odds,
    )

    return NFLMoneylineEdge(
        game_id=snapshot.game_id,
        home_team_id=snapshot.home_team_id,
        away_team_id=snapshot.away_team_id,
        provider=snapshot.provider,
        observed_timestamp=snapshot.observed_timestamp,
        home_american_odds=snapshot.home_american_odds,
        away_american_odds=snapshot.away_american_odds,
        home_market_implied_probability=fair.home_implied_probability,
        away_market_implied_probability=fair.away_implied_probability,
        home_market_fair_probability=fair.home_fair_probability,
        away_market_fair_probability=fair.away_fair_probability,
        home_calibrated_model_probability=home_calibrated_model_probability,
        away_calibrated_model_probability=away_calibrated_model_probability,
        home_edge=(
            home_calibrated_model_probability - fair.home_fair_probability
        ),
        away_edge=(
            away_calibrated_model_probability - fair.away_fair_probability
        ),
    )


def _validate_probability(probability: float, field_name: str) -> None:
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    numeric_probability = float(probability)
    if not math.isfinite(numeric_probability):
        raise ValueError(f"{field_name} must be finite.")

    if not 0.0 <= numeric_probability <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1.")
