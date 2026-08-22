from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from gridiron.market import (
    NFLMoneylineSnapshot,
    american_odds_to_implied_probability,
    remove_two_sided_vig,
)


def _snapshot(**overrides: object) -> NFLMoneylineSnapshot:
    values = {
        "game_id": "2026_01_BUF_NYJ",
        "home_team_id": "NYJ",
        "away_team_id": "BUF",
        "provider": "example-provider",
        "observed_timestamp": datetime(2026, 9, 1, 12, tzinfo=UTC),
        "home_american_odds": 120,
        "away_american_odds": -140,
    }
    values.update(overrides)
    return NFLMoneylineSnapshot(**values)  # type: ignore[arg-type]


def test_snapshot_is_immutable_and_preserves_raw_odds() -> None:
    snapshot = _snapshot()

    assert snapshot.home_american_odds == 120
    assert snapshot.away_american_odds == -140
    with pytest.raises(FrozenInstanceError):
        snapshot.provider = "another-provider"  # type: ignore[misc]


def test_positive_and_negative_american_odds_conversion() -> None:
    assert american_odds_to_implied_probability(200) == pytest.approx(1 / 3)
    assert american_odds_to_implied_probability(-150) == pytest.approx(0.6)


def test_vig_removal_preserves_implied_and_fair_probabilities() -> None:
    probabilities = remove_two_sided_vig(-150, 130)

    assert probabilities.home_implied_probability == pytest.approx(0.6)
    assert probabilities.away_implied_probability == pytest.approx(100 / 230)
    assert (
        probabilities.home_fair_probability
        + probabilities.away_fair_probability
    ) == pytest.approx(1.0)


def test_vig_removal_is_symmetric() -> None:
    original = remove_two_sided_vig(-120, 105)
    reversed_market = remove_two_sided_vig(105, -120)

    assert original.home_implied_probability == reversed_market.away_implied_probability
    assert original.home_fair_probability == reversed_market.away_fair_probability
    assert remove_two_sided_vig(-110, -110).home_fair_probability == pytest.approx(
        0.5
    )


def test_conversion_is_deterministic() -> None:
    assert remove_two_sided_vig(-135, 115) == remove_two_sided_vig(-135, 115)


@pytest.mark.parametrize("invalid_odds", [True, 100.5, "-110", None])
def test_non_integer_american_odds_are_rejected(invalid_odds: object) -> None:
    with pytest.raises(TypeError, match="integer"):
        american_odds_to_implied_probability(invalid_odds)  # type: ignore[arg-type]


def test_zero_american_odds_are_rejected() -> None:
    with pytest.raises(ValueError, match="zero"):
        remove_two_sided_vig(-110, 0)


@pytest.mark.parametrize(
    ("overrides", "error", "message"),
    [
        ({"game_id": " "}, ValueError, "game_id"),
        ({"provider": ""}, ValueError, "provider"),
        ({"away_team_id": "NYJ"}, ValueError, "different"),
        (
            {"observed_timestamp": datetime(2026, 9, 1, 12)},  # noqa: DTZ001
            ValueError,
            "timezone-aware",
        ),
        ({"observed_timestamp": "2026-09-01T12:00:00Z"}, TypeError, "datetime"),
        ({"home_american_odds": 0}, ValueError, "zero"),
    ],
)
def test_invalid_snapshots_are_rejected(
    overrides: dict[str, object],
    error: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error, match=message):
        _snapshot(**overrides)

