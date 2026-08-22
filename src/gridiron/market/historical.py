"""Historical NFL moneyline research records."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class NFLHistoricalMoneylineRecord:
    """Immutable historical market/model/outcome record for one NFL game."""

    season: int
    week: int
    game_id: str
    home_team_id: str
    away_team_id: str
    provider: str
    observed_timestamp: datetime

    home_american_odds: int
    away_american_odds: int

    home_calibrated_model_probability: float
    away_calibrated_model_probability: float

    winning_team_id: str

    def __post_init__(self) -> None:
        _validate_positive_integer(self.season, "season")
        _validate_positive_integer(self.week, "week")

        for field_name in (
            "game_id",
            "home_team_id",
            "away_team_id",
            "provider",
            "winning_team_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string.")

        if self.home_team_id == self.away_team_id:
            raise ValueError("home_team_id and away_team_id must be different.")

        if self.winning_team_id not in (self.home_team_id, self.away_team_id):
            raise ValueError(
                "winning_team_id must match either home_team_id or away_team_id."
            )

        if not isinstance(self.observed_timestamp, datetime):
            raise TypeError("observed_timestamp must be a datetime.")

        if (
            self.observed_timestamp.tzinfo is None
            or self.observed_timestamp.utcoffset() is None
        ):
            raise ValueError("observed_timestamp must be timezone-aware.")

        _validate_american_odds(self.home_american_odds)
        _validate_american_odds(self.away_american_odds)

        _validate_probability(
            self.home_calibrated_model_probability,
            "home_calibrated_model_probability",
        )
        _validate_probability(
            self.away_calibrated_model_probability,
            "away_calibrated_model_probability",
        )

        probability_total = (
            self.home_calibrated_model_probability
            + self.away_calibrated_model_probability
        )
        if not math.isclose(
            probability_total,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "Calibrated home and away probabilities must sum to 1.0."
            )


def _validate_positive_integer(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value <= 0:
        raise ValueError(f"{field_name} must be positive.")


def _validate_american_odds(american_odds: int) -> None:
    if isinstance(american_odds, bool) or not isinstance(american_odds, int):
        raise TypeError("American odds must be an integer.")

    if american_odds == 0:
        raise ValueError("American odds cannot be zero.")


def _validate_probability(probability: float, field_name: str) -> None:
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    numeric_probability = float(probability)
    if not math.isfinite(numeric_probability):
        raise ValueError(f"{field_name} must be finite.")

    if not 0.0 <= numeric_probability <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1.")
