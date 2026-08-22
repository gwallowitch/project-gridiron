from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from gridiron.market.expected_value import (
    NFLMoneylineExpectedValue,
    calculate_moneyline_expected_value,
)


def test_positive_odds_expected_value() -> None:
    result = calculate_moneyline_expected_value(
        american_odds=200,
        calibrated_model_probability=0.40,
    )

    assert result.american_odds == 200
    assert result.calibrated_model_probability == pytest.approx(0.40)
    assert result.market_implied_probability == pytest.approx(1 / 3)
    assert result.profit_per_unit_stake == pytest.approx(2.0)
    assert result.expected_profit_per_unit_stake == pytest.approx(0.20)
    assert result.expected_roi == pytest.approx(0.20)


def test_negative_odds_expected_value() -> None:
    result = calculate_moneyline_expected_value(
        american_odds=-150,
        calibrated_model_probability=0.65,
    )

    assert result.market_implied_probability == pytest.approx(0.60)
    assert result.profit_per_unit_stake == pytest.approx(2 / 3)
    assert result.expected_profit_per_unit_stake == pytest.approx(
        0.65 * (2 / 3) - 0.35
    )


def test_break_even_probability_has_zero_expected_value() -> None:
    result = calculate_moneyline_expected_value(
        american_odds=-110,
        calibrated_model_probability=110 / 210,
    )

    assert result.expected_profit_per_unit_stake == pytest.approx(0.0)
    assert result.expected_roi == pytest.approx(0.0)


def test_expected_value_can_be_negative() -> None:
    result = calculate_moneyline_expected_value(
        american_odds=150,
        calibrated_model_probability=0.35,
    )

    assert result.expected_profit_per_unit_stake < 0.0


def test_expected_value_result_is_immutable() -> None:
    result = calculate_moneyline_expected_value(
        american_odds=120,
        calibrated_model_probability=0.50,
    )

    assert isinstance(result, NFLMoneylineExpectedValue)
    with pytest.raises(FrozenInstanceError):
        result.expected_roi = 0.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("probability", "error"),
    [
        (-0.01, ValueError),
        (1.01, ValueError),
        (float("nan"), ValueError),
        (float("inf"), ValueError),
        ("0.5", TypeError),
        (True, TypeError),
    ],
)
def test_invalid_model_probability_is_rejected(
    probability: object,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        calculate_moneyline_expected_value(
            american_odds=-110,
            calibrated_model_probability=probability,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("american_odds", "error"),
    [
        (0, ValueError),
        (100.5, TypeError),
        ("-110", TypeError),
        (True, TypeError),
    ],
)
def test_invalid_american_odds_are_rejected(
    american_odds: object,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        calculate_moneyline_expected_value(
            american_odds=american_odds,  # type: ignore[arg-type]
            calibrated_model_probability=0.50,
        )
