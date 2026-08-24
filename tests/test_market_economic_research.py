from __future__ import annotations

import pytest

from gridiron.market.economic_research import (
    NFLEconomicObservation,
    fixed_absolute_adjustment_bucket,
    summarize_economic_bucket,
)


def test_positive_american_odds_profit() -> None:
    observation = NFLEconomicObservation(
        game_id="G1",
        side="HOME",
        candidate_probability=0.50,
        offered_american_odds=150,
        won=True,
    )

    assert observation.flat_bet_profit == pytest.approx(1.5)


def test_negative_american_odds_profit() -> None:
    observation = NFLEconomicObservation(
        game_id="G1",
        side="HOME",
        candidate_probability=0.60,
        offered_american_odds=-200,
        won=True,
    )

    assert observation.flat_bet_profit == pytest.approx(0.5)


def test_losing_bet_loses_one_unit() -> None:
    observation = NFLEconomicObservation(
        game_id="G1",
        side="AWAY",
        candidate_probability=0.40,
        offered_american_odds=120,
        won=False,
    )

    assert observation.flat_bet_profit == -1.0


def test_probability_edge_uses_offered_break_even_price() -> None:
    observation = NFLEconomicObservation(
        game_id="G1",
        side="HOME",
        candidate_probability=0.55,
        offered_american_odds=-110,
        won=True,
    )

    assert observation.break_even_probability == pytest.approx(
        110 / 210
    )
    assert observation.probability_edge == pytest.approx(
        0.55 - (110 / 210)
    )


def test_economic_bucket_summary() -> None:
    observations = (
        NFLEconomicObservation(
            game_id="G1",
            side="HOME",
            candidate_probability=0.60,
            offered_american_odds=-110,
            won=True,
        ),
        NFLEconomicObservation(
            game_id="G2",
            side="HOME",
            candidate_probability=0.55,
            offered_american_odds=120,
            won=False,
        ),
    )

    result = summarize_economic_bucket(
        label="example",
        observations=observations,
    )

    assert result.bets == 2
    assert result.wins == 1
    assert result.losses == 1
    assert result.total_profit == pytest.approx(
        (100 / 110) - 1.0
    )
    assert result.roi == pytest.approx(
        ((100 / 110) - 1.0) / 2
    )


@pytest.mark.parametrize(
    ("adjustment", "expected"),
    [
        (0.000, "<1%"),
        (0.0099, "<1%"),
        (0.0100, "1-2%"),
        (-0.0199, "1-2%"),
        (0.0200, "2-3%"),
        (-0.0299, "2-3%"),
        (0.0300, "3-4.25%"),
        (-0.0425, "3-4.25%"),
    ],
)
def test_fixed_absolute_adjustment_bucket(
    adjustment: float,
    expected: str,
) -> None:
    assert fixed_absolute_adjustment_bucket(
        adjustment
    ) == expected


def test_empty_economic_bucket_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="requires at least one observation",
    ):
        summarize_economic_bucket(
            label="empty",
            observations=(),
        )
