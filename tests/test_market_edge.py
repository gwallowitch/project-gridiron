from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from gridiron.market.edge import NFLMoneylineEdge, calculate_moneyline_edge
from gridiron.market.moneyline import NFLMoneylineSnapshot


def _snapshot() -> NFLMoneylineSnapshot:
    return NFLMoneylineSnapshot(
        game_id="2026_01_BUF_NYJ",
        home_team_id="NYJ",
        away_team_id="BUF",
        provider="example-provider",
        observed_timestamp=datetime(2026, 9, 1, 12, tzinfo=UTC),
        home_american_odds=120,
        away_american_odds=-140,
    )


def test_calculate_moneyline_edge_preserves_inputs() -> None:
    snapshot = _snapshot()

    result = calculate_moneyline_edge(
        snapshot,
        home_calibrated_model_probability=0.48,
        away_calibrated_model_probability=0.52,
    )

    assert result.game_id == snapshot.game_id
    assert result.provider == snapshot.provider
    assert result.observed_timestamp == snapshot.observed_timestamp
    assert result.home_american_odds == 120
    assert result.away_american_odds == -140
    assert result.home_calibrated_model_probability == pytest.approx(0.48)
    assert result.away_calibrated_model_probability == pytest.approx(0.52)


def test_calculate_moneyline_edge_preserves_market_probabilities() -> None:
    result = calculate_moneyline_edge(
        _snapshot(),
        home_calibrated_model_probability=0.48,
        away_calibrated_model_probability=0.52,
    )

    assert result.home_market_implied_probability == pytest.approx(100 / 220)
    assert result.away_market_implied_probability == pytest.approx(140 / 240)
    assert (
        result.home_market_fair_probability + result.away_market_fair_probability
    ) == pytest.approx(1.0)


def test_edge_is_model_probability_minus_fair_market_probability() -> None:
    result = calculate_moneyline_edge(
        _snapshot(),
        home_calibrated_model_probability=0.48,
        away_calibrated_model_probability=0.52,
    )

    assert result.home_edge == pytest.approx(
        result.home_calibrated_model_probability
        - result.home_market_fair_probability
    )
    assert result.away_edge == pytest.approx(
        result.away_calibrated_model_probability
        - result.away_market_fair_probability
    )


def test_home_and_away_edges_are_complements() -> None:
    result = calculate_moneyline_edge(
        _snapshot(),
        home_calibrated_model_probability=0.48,
        away_calibrated_model_probability=0.52,
    )

    assert result.home_edge + result.away_edge == pytest.approx(0.0)


def test_edge_result_is_immutable() -> None:
    result = calculate_moneyline_edge(
        _snapshot(),
        home_calibrated_model_probability=0.48,
        away_calibrated_model_probability=0.52,
    )

    assert isinstance(result, NFLMoneylineEdge)
    with pytest.raises(FrozenInstanceError):
        result.home_edge = 0.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("home_probability", "away_probability", "error"),
    [
        (-0.01, 1.01, ValueError),
        (1.01, -0.01, ValueError),
        (float("nan"), 0.5, ValueError),
        (float("inf"), 0.0, ValueError),
        ("0.5", 0.5, TypeError),
        (True, 0.0, TypeError),
    ],
)
def test_invalid_calibrated_probabilities_are_rejected(
    home_probability: object,
    away_probability: object,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        calculate_moneyline_edge(
            _snapshot(),
            home_calibrated_model_probability=home_probability,  # type: ignore[arg-type]
            away_calibrated_model_probability=away_probability,  # type: ignore[arg-type]
        )


def test_calibrated_probabilities_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        calculate_moneyline_edge(
            _snapshot(),
            home_calibrated_model_probability=0.60,
            away_calibrated_model_probability=0.45,
        )
