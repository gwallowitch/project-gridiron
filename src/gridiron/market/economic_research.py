"""Economic evaluation helpers for frozen market-residual probabilities."""

from __future__ import annotations

from dataclasses import dataclass

from gridiron.market.moneyline import (
    american_odds_to_implied_probability,
)


@dataclass(frozen=True, slots=True)
class NFLEconomicObservation:
    """One settled wager-side observation for economic research."""

    game_id: str
    side: str
    candidate_probability: float
    offered_american_odds: int
    won: bool

    @property
    def break_even_probability(self) -> float:
        """Return the raw break-even probability implied by the offered price."""
        return american_odds_to_implied_probability(
            self.offered_american_odds
        )

    @property
    def probability_edge(self) -> float:
        """Candidate probability minus offered-price break-even probability."""
        return (
            self.candidate_probability
            - self.break_even_probability
        )

    @property
    def flat_bet_profit(self) -> float:
        """Profit from risking one unit at the offered American price."""
        if not self.won:
            return -1.0

        if self.offered_american_odds > 0:
            return self.offered_american_odds / 100.0

        return 100.0 / abs(self.offered_american_odds)


@dataclass(frozen=True, slots=True)
class NFLEconomicBucketSummary:
    """Descriptive performance for one fixed economic bucket."""

    label: str
    bets: int
    wins: int
    losses: int
    mean_probability_edge: float
    total_profit: float
    roi: float


def summarize_economic_bucket(
    *,
    label: str,
    observations: tuple[NFLEconomicObservation, ...],
) -> NFLEconomicBucketSummary:
    """Summarize one fixed group of economic observations."""
    if not observations:
        raise ValueError("Economic bucket requires at least one observation.")

    wins = sum(observation.won for observation in observations)
    losses = len(observations) - wins
    total_profit = sum(
        observation.flat_bet_profit
        for observation in observations
    )

    return NFLEconomicBucketSummary(
        label=label,
        bets=len(observations),
        wins=wins,
        losses=losses,
        mean_probability_edge=sum(
            observation.probability_edge
            for observation in observations
        )
        / len(observations),
        total_profit=total_profit,
        roi=total_profit / len(observations),
    )


def fixed_absolute_adjustment_bucket(
    adjustment: float,
) -> str:
    """Assign frozen probability movement to a descriptive fixed bucket."""
    absolute_adjustment = abs(adjustment)

    if absolute_adjustment < 0.01:
        return "<1%"
    if absolute_adjustment < 0.02:
        return "1-2%"
    if absolute_adjustment < 0.03:
        return "2-3%"
    return "3-4.25%"
