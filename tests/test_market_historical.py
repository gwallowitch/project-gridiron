from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from gridiron.market.historical import NFLHistoricalMoneylineRecord


def _record(**overrides: object) -> NFLHistoricalMoneylineRecord:
    values = {
        "season": 2025,
        "week": 8,
        "game_id": "2025_08_BUF_NYJ",
        "home_team_id": "NYJ",
        "away_team_id": "BUF",
        "provider": "example-provider",
        "observed_timestamp": datetime(2025, 10, 26, 12, tzinfo=UTC),
        "home_american_odds": 135,
        "away_american_odds": -155,
        "home_calibrated_model_probability": 0.44,
        "away_calibrated_model_probability": 0.56,
        "winning_team_id": "BUF",
    }
    values.update(overrides)
    return NFLHistoricalMoneylineRecord(**values)  # type: ignore[arg-type]


def test_historical_record_preserves_market_model_and_outcome() -> None:
    record = _record()

    assert record.season == 2025
    assert record.week == 8
    assert record.game_id == "2025_08_BUF_NYJ"
    assert record.home_american_odds == 135
    assert record.away_american_odds == -155
    assert record.home_calibrated_model_probability == pytest.approx(0.44)
    assert record.away_calibrated_model_probability == pytest.approx(0.56)
    assert record.winning_team_id == "BUF"


def test_historical_record_is_immutable() -> None:
    record = _record()

    with pytest.raises(FrozenInstanceError):
        record.week = 9  # type: ignore[misc]


@pytest.mark.parametrize(
    ("overrides", "error", "message"),
    [
        ({"season": 0}, ValueError, "season"),
        ({"season": 2025.0}, TypeError, "season"),
        ({"week": 0}, ValueError, "week"),
        ({"week": True}, TypeError, "week"),
        ({"game_id": " "}, ValueError, "game_id"),
        ({"provider": ""}, ValueError, "provider"),
        ({"away_team_id": "NYJ"}, ValueError, "different"),
        ({"winning_team_id": "MIA"}, ValueError, "winning_team_id"),
        (
            {"observed_timestamp": datetime(2025, 10, 26, 12)},  # noqa: DTZ001
            ValueError,
            "timezone-aware",
        ),
        (
            {"observed_timestamp": "2025-10-26T12:00:00Z"},
            TypeError,
            "datetime",
        ),
        ({"home_american_odds": 0}, ValueError, "zero"),
        ({"away_american_odds": True}, TypeError, "integer"),
        (
            {"home_calibrated_model_probability": float("nan")},
            ValueError,
            "finite",
        ),
        (
            {"away_calibrated_model_probability": 1.01},
            ValueError,
            "between 0 and 1",
        ),
    ],
)
def test_invalid_historical_records_are_rejected(
    overrides: dict[str, object],
    error: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error, match=message):
        _record(**overrides)


def test_historical_model_probabilities_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        _record(
            home_calibrated_model_probability=0.60,
            away_calibrated_model_probability=0.45,
        )
