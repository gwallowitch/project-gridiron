from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from gridiron.market.eligibility import (
    NFLMoneylineEligibilityThresholds,
    NFLMoneylineGameEligibility,
    evaluate_moneyline_eligibility,
)
from gridiron.market.evaluation import evaluate_moneyline_game
from gridiron.market.moneyline import NFLMoneylineSnapshot


def _evaluation(
    *,
    home_probability: float = 0.48,
    away_probability: float = 0.52,
):
    snapshot = NFLMoneylineSnapshot(
        game_id="2026_01_BUF_NYJ",
        home_team_id="NYJ",
        away_team_id="BUF",
        provider="example-provider",
        observed_timestamp=datetime(2026, 9, 1, 12, tzinfo=UTC),
        home_american_odds=120,
        away_american_odds=-140,
    )
    return evaluate_moneyline_game(
        snapshot,
        home_calibrated_model_probability=home_probability,
        away_calibrated_model_probability=away_probability,
    )


def test_zero_thresholds_allow_positive_edge_and_roi_side() -> None:
    result = evaluate_moneyline_eligibility(
        _evaluation(),
        thresholds=NFLMoneylineEligibilityThresholds(),
    )

    assert isinstance(result, NFLMoneylineGameEligibility)
    assert result.home.eligible is True
    assert result.home.rejection_reasons == ()
    assert result.home.edge > 0.0
    assert result.home.expected_roi > 0.0


def test_side_can_fail_edge_threshold_only() -> None:
    result = evaluate_moneyline_eligibility(
        _evaluation(),
        thresholds=NFLMoneylineEligibilityThresholds(
            minimum_edge=0.05,
            minimum_expected_roi=0.0,
        ),
    )

    assert result.home.eligible is False
    assert result.home.rejection_reasons == ("edge_below_minimum",)


def test_side_can_fail_expected_roi_threshold_only() -> None:
    result = evaluate_moneyline_eligibility(
        _evaluation(),
        thresholds=NFLMoneylineEligibilityThresholds(
            minimum_edge=0.0,
            minimum_expected_roi=0.07,
        ),
    )

    assert result.home.eligible is False
    assert result.home.rejection_reasons == ("expected_roi_below_minimum",)


def test_side_can_fail_multiple_thresholds() -> None:
    result = evaluate_moneyline_eligibility(
        _evaluation(),
        thresholds=NFLMoneylineEligibilityThresholds(
            minimum_edge=0.05,
            minimum_expected_roi=0.07,
        ),
    )

    assert result.home.eligible is False
    assert result.home.rejection_reasons == (
        "edge_below_minimum",
        "expected_roi_below_minimum",
    )


def test_home_and_away_are_evaluated_independently() -> None:
    result = evaluate_moneyline_eligibility(
        _evaluation(),
        thresholds=NFLMoneylineEligibilityThresholds(),
    )

    assert result.home.eligible is True
    assert result.away.eligible is False
    assert result.away.rejection_reasons == (
        "edge_below_minimum",
        "expected_roi_below_minimum",
    )


def test_threshold_boundary_is_inclusive() -> None:
    evaluation = _evaluation()

    result = evaluate_moneyline_eligibility(
        evaluation,
        thresholds=NFLMoneylineEligibilityThresholds(
            minimum_edge=evaluation.edge.home_edge,
            minimum_expected_roi=evaluation.home_expected_value.expected_roi,
        ),
    )

    assert result.home.eligible is True


def test_eligibility_result_is_immutable() -> None:
    result = evaluate_moneyline_eligibility(
        _evaluation(),
        thresholds=NFLMoneylineEligibilityThresholds(),
    )

    with pytest.raises(FrozenInstanceError):
        result.home = result.home  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "value", "error"),
    [
        ("minimum_edge", float("nan"), ValueError),
        ("minimum_edge", float("inf"), ValueError),
        ("minimum_edge", "0.02", TypeError),
        ("minimum_edge", True, TypeError),
        ("minimum_expected_roi", float("nan"), ValueError),
        ("minimum_expected_roi", "0.05", TypeError),
    ],
)
def test_invalid_thresholds_are_rejected(
    field_name: str,
    value: object,
    error: type[Exception],
) -> None:
    kwargs = {field_name: value}

    with pytest.raises(error):
        NFLMoneylineEligibilityThresholds(**kwargs)  # type: ignore[arg-type]

