"""Configurable NFL moneyline bet-eligibility research rules."""

from __future__ import annotations

import math
from dataclasses import dataclass

from gridiron.market.evaluation import NFLMoneylineGameEvaluation


@dataclass(frozen=True, slots=True)
class NFLMoneylineEligibilityThresholds:
    """Configurable research thresholds for moneyline eligibility."""

    minimum_edge: float = 0.0
    minimum_expected_roi: float = 0.0

    def __post_init__(self) -> None:
        _validate_threshold(self.minimum_edge, "minimum_edge")
        _validate_threshold(self.minimum_expected_roi, "minimum_expected_roi")


@dataclass(frozen=True, slots=True)
class NFLMoneylineSideEligibility:
    """Eligibility result for one side of a moneyline."""

    eligible: bool
    edge: float
    expected_roi: float
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NFLMoneylineGameEligibility:
    """Independent home and away eligibility results for one game."""

    home: NFLMoneylineSideEligibility
    away: NFLMoneylineSideEligibility


def evaluate_moneyline_eligibility(
    evaluation: NFLMoneylineGameEvaluation,
    *,
    thresholds: NFLMoneylineEligibilityThresholds,
) -> NFLMoneylineGameEligibility:
    """Evaluate both moneyline sides without selecting or sizing a bet."""
    home = _evaluate_side(
        edge=evaluation.edge.home_edge,
        expected_roi=evaluation.home_expected_value.expected_roi,
        thresholds=thresholds,
    )
    away = _evaluate_side(
        edge=evaluation.edge.away_edge,
        expected_roi=evaluation.away_expected_value.expected_roi,
        thresholds=thresholds,
    )

    return NFLMoneylineGameEligibility(
        home=home,
        away=away,
    )


def _evaluate_side(
    *,
    edge: float,
    expected_roi: float,
    thresholds: NFLMoneylineEligibilityThresholds,
) -> NFLMoneylineSideEligibility:
    rejection_reasons: list[str] = []

    if edge < thresholds.minimum_edge:
        rejection_reasons.append("edge_below_minimum")

    if expected_roi < thresholds.minimum_expected_roi:
        rejection_reasons.append("expected_roi_below_minimum")

    return NFLMoneylineSideEligibility(
        eligible=not rejection_reasons,
        edge=edge,
        expected_roi=expected_roi,
        rejection_reasons=tuple(rejection_reasons),
    )


def _validate_threshold(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")

    if not math.isfinite(float(value)):
        raise ValueError(f"{field_name} must be finite.")
