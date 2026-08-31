from __future__ import annotations

from copy import deepcopy

import pytest

from gridiron.market.core_three_provider import (
    assert_external_gates,
    normalize_event_response,
    parse_timestamp,
)
from gridiron.market.core_three_types import BOOK_KEYS, CoreThreeError, MARKET_KEYS


def authoritative() -> dict[str, object]:
    return {
        "game_id": "2026_01_NE_SEA",
        "provider_event_id": "provider-event-1",
        "home_team": "Seattle Seahawks",
        "away_team": "New England Patriots",
        "kickoff_at": "2026-09-10T00:20:00Z",
    }


def response() -> dict[str, object]:
    home = "Seattle Seahawks"
    away = "New England Patriots"
    return {
        "id": "provider-event-1",
        "home_team": home,
        "away_team": away,
        "commence_time": "2026-09-10T00:20:00Z",
        "bookmakers": [
            {
                "key": key,
                "title": {"betmgm": "BetMGM", "fanduel": "FanDuel", "draftkings": "DraftKings"}[key],
                "sid": f"{key}-sid",
                "markets": [
                    {
                        "key": "h2h",
                        "last_update": "2026-09-09T23:19:00Z",
                        "outcomes": [
                            {"name": away, "price": 155, "sid": f"{key}-away"},
                            {"name": home, "price": -190, "sid": f"{key}-home"},
                        ],
                    },
                    {
                        "key": "spreads",
                        "last_update": "2026-09-09T23:19:00Z",
                        "outcomes": [
                            {"name": away, "price": -110, "point": 3.5},
                            {"name": home, "price": -110, "point": -3.5},
                        ],
                    },
                    {
                        "key": "totals",
                        "last_update": "2026-09-09T23:19:00Z",
                        "outcomes": [
                            {"name": "Over", "price": -110, "point": 44.5},
                            {"name": "Under", "price": -110, "point": 44.5},
                        ],
                    },
                ],
            }
            for key in BOOK_KEYS
        ],
    }


def normalize(payload: dict[str, object] | None = None):
    return normalize_event_response(
        payload or response(),
        authoritative(),
        receipt_at="2026-09-09T23:20:00Z",
        timestamp_semantics_approved=True,
    )


def test_exact_core_three_and_three_markets_are_accepted() -> None:
    observation = normalize()
    assert tuple(book.key for book in observation.books) == BOOK_KEYS
    assert all(tuple(m.key for m in book.markets) == MARKET_KEYS for book in observation.books)
    assert observation.raw_payload_retained is False
    assert observation.prospective_evidence is False


@pytest.mark.parametrize("key", BOOK_KEYS)
def test_each_missing_required_book_rejects(key: str) -> None:
    payload = response()
    payload["bookmakers"] = [b for b in payload["bookmakers"] if b["key"] != key]
    with pytest.raises(CoreThreeError, match="BOOK_UNIVERSE_MISMATCH"):
        normalize(payload)


@pytest.mark.parametrize("key", ["BetMGM", "Bet MGM", "caesars", "bet365", "draftkings_us"])
def test_alias_generic_extra_and_regional_keys_reject(key: str) -> None:
    payload = response()
    payload["bookmakers"][0]["key"] = key
    with pytest.raises(CoreThreeError, match="BOOK_UNIVERSE_MISMATCH"):
        normalize(payload)


def test_duplicate_bookmaker_rejects() -> None:
    payload = response()
    payload["bookmakers"][1] = deepcopy(payload["bookmakers"][0])
    with pytest.raises(CoreThreeError, match="DUPLICATE_BOOKMAKER"):
        normalize(payload)


@pytest.mark.parametrize("market", MARKET_KEYS)
def test_each_missing_market_rejects(market: str) -> None:
    payload = response()
    payload["bookmakers"][0]["markets"] = [
        m for m in payload["bookmakers"][0]["markets"] if m["key"] != market
    ]
    with pytest.raises(CoreThreeError, match="MARKET_UNIVERSE_MISMATCH"):
        normalize(payload)


def test_duplicate_market_rejects_even_when_identical() -> None:
    payload = response()
    payload["bookmakers"][0]["markets"][1] = deepcopy(
        payload["bookmakers"][0]["markets"][0]
    )
    with pytest.raises(CoreThreeError, match="DUPLICATE_MARKET"):
        normalize(payload)


@pytest.mark.parametrize("key", ["alternate_spreads", "alternate_totals"])
def test_alternate_market_rejects(key: str) -> None:
    payload = response()
    payload["bookmakers"][0]["markets"][1]["key"] = key
    with pytest.raises(CoreThreeError, match="MARKET_UNIVERSE_MISMATCH"):
        normalize(payload)


def test_suspended_market_rejects() -> None:
    payload = response()
    payload["bookmakers"][0]["markets"][0]["suspended"] = True
    with pytest.raises(CoreThreeError, match="SUSPENDED_MARKET"):
        normalize(payload)


@pytest.mark.parametrize(
    ("market_index", "mutation", "message"),
    [
        (0, lambda m: m["outcomes"].pop(), "INCOMPLETE_OUTCOMES"),
        (0, lambda m: m["outcomes"][0].update(price=None), "MALFORMED_PRICE"),
        (0, lambda m: m["outcomes"][0].update(price=99), "MALFORMED_PRICE"),
        (0, lambda m: m["outcomes"].append({"name": "Draw", "price": 200}), "INCOMPLETE_OUTCOMES"),
        (1, lambda m: m["outcomes"][0].update(point=4.0), "CONFLICTING_LINE"),
        (2, lambda m: m["outcomes"][1].update(point=45.0), "CONFLICTING_LINE"),
    ],
)
def test_malformed_incomplete_three_way_and_conflicting_markets_reject(
    market_index: int, mutation, message: str
) -> None:
    payload = response()
    mutation(payload["bookmakers"][0]["markets"][market_index])
    with pytest.raises(CoreThreeError, match=message):
        normalize(payload)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("id", "wrong", "EVENT_ID_MISMATCH"),
        ("home_team", "New England Patriots", "HOME_TEAM_MISMATCH"),
        ("away_team", "Seattle Seahawks", "AWAY_TEAM_MISMATCH"),
        ("commence_time", "2026-09-10T00:15:00Z", "KICKOFF_MISMATCH"),
    ],
)
def test_event_identity_and_five_minute_kickoff_mismatch_reject(
    field: str, value: str, message: str
) -> None:
    payload = response()
    payload[field] = value
    with pytest.raises(CoreThreeError, match=message):
        normalize(payload)


@pytest.mark.parametrize(
    ("timestamp", "message"),
    [
        ("2026-09-09T23:09:59Z", "STALE_QUOTE"),
        ("2026-09-09T23:21:00Z", "FUTURE_QUOTE"),
        ("2026-09-09T23:19:00", "TIMEZONE_REQUIRED"),
        ("invalid", "INVALID_TIMESTAMP"),
    ],
)
def test_stale_future_naive_and_invalid_timestamp_reject(
    timestamp: str, message: str
) -> None:
    payload = response()
    payload["bookmakers"][0]["markets"][0]["last_update"] = timestamp
    with pytest.raises(CoreThreeError, match=message):
        normalize(payload)


def test_timezone_normalization_is_utc() -> None:
    assert parse_timestamp("2026-09-09T18:20:00-05:00", "test").isoformat() == (
        "2026-09-09T23:20:00+00:00"
    )


def test_timestamp_semantics_gate_is_explicit() -> None:
    with pytest.raises(CoreThreeError, match="TIMESTAMP_SEMANTICS_UNAPPROVED"):
        normalize_event_response(
            response(),
            authoritative(),
            receipt_at="2026-09-09T23:20:00Z",
            timestamp_semantics_approved=False,
        )


def test_every_external_activation_gate_fails_closed() -> None:
    with pytest.raises(CoreThreeError, match="EXTERNAL_GATES_BLOCKED"):
        assert_external_gates(
            timestamp_semantics_approved=False,
            jurisdiction_approved=False,
            draftkings_execution_state_approved=False,
            retention_approved=False,
            authoritative_kickoff_approved=False,
            governance_approved=False,
            effective_timestamp=None,
        )

def test_timestamp_semantics_alone_blocks_activation() -> None:
    with pytest.raises(
        CoreThreeError,
        match="TIMESTAMP_SEMANTICS_UNAPPROVED",
    ):
        assert_external_gates(
            timestamp_semantics_approved=False,
            jurisdiction_approved=True,
            draftkings_execution_state_approved=True,
            retention_approved=True,
            authoritative_kickoff_approved=True,
            governance_approved=True,
            effective_timestamp="2026-09-01T00:00:00Z",
        )
