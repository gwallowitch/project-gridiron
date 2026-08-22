"""Typed NFL moneyline observations and pure probability conversions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class NFLMoneylineSnapshot:
    """A provider's immutable observation of a two-sided NFL moneyline."""

    game_id: str
    home_team_id: str
    away_team_id: str
    provider: str
    observed_timestamp: datetime
    home_american_odds: int
    away_american_odds: int

    def __post_init__(self) -> None:
        for field_name in ("game_id", "home_team_id", "away_team_id", "provider"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string.")

        if self.home_team_id == self.away_team_id:
            raise ValueError("home_team_id and away_team_id must be different.")

        if not isinstance(self.observed_timestamp, datetime):
            raise TypeError("observed_timestamp must be a datetime.")

        if (
            self.observed_timestamp.tzinfo is None
            or self.observed_timestamp.utcoffset() is None
        ):
            raise ValueError("observed_timestamp must be timezone-aware.")

        _validate_american_odds(self.home_american_odds)
        _validate_american_odds(self.away_american_odds)


@dataclass(frozen=True, slots=True)
class FairMoneylineProbabilities:
    """Raw implied and normalized probabilities for a two-sided moneyline."""

    home_implied_probability: float
    away_implied_probability: float
    home_fair_probability: float
    away_fair_probability: float


def american_odds_to_implied_probability(american_odds: int) -> float:
    """Convert nonzero integer American odds to implied probability."""
    _validate_american_odds(american_odds)
    if american_odds > 0:
        return 100.0 / (american_odds + 100.0)

    absolute_odds = abs(american_odds)
    return absolute_odds / (absolute_odds + 100.0)


def remove_two_sided_vig(
    home_american_odds: int,
    away_american_odds: int,
) -> FairMoneylineProbabilities:
    """Return raw implied and proportionally normalized fair probabilities."""
    home_implied = american_odds_to_implied_probability(home_american_odds)
    away_implied = american_odds_to_implied_probability(away_american_odds)
    implied_total = home_implied + away_implied

    return FairMoneylineProbabilities(
        home_implied_probability=home_implied,
        away_implied_probability=away_implied,
        home_fair_probability=home_implied / implied_total,
        away_fair_probability=away_implied / implied_total,
    )


def _validate_american_odds(american_odds: int) -> None:
    if isinstance(american_odds, bool) or not isinstance(american_odds, int):
        raise TypeError("American odds must be an integer.")
    if american_odds == 0:
        raise ValueError("American odds cannot be zero.")
