from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from gridiron.market.operational_history import canonical_json
from gridiron.market.operational_spreads import (
    BOOK_KEYS,
    ImmutableSpreadConflictError,
    OperationalSpreadError,
    append_spread_observation,
    build_spread_observation,
    read_spread_history,
    validate_spread_observation,
)

KICKOFF = datetime(2026, 9, 20, 17, tzinfo=UTC)
COLLECTED = KICKOFF - timedelta(minutes=60)
RAW_ID = "a" * 64
PAYLOAD_SHA = "b" * 64


def game() -> dict[str, object]:
    return {
        "game_id": "2026_02_SEA_SF",
        "season": 2026,
        "week": 2,
        "season_type": "REG",
        "home_team": "SF",
        "away_team": "SEA",
        "kickoff_at": "2026-09-20T17:00:00Z",
    }


def book(
    key: str,
    home_points: float = -3.5,
    away_points: float = 3.5,
    home_price: int = -108,
    away_price: int = -112,
    *,
    age: int = 2,
) -> dict[str, object]:
    names = {"betmgm": "BetMGM", "fanduel": "FanDuel", "draftkings": "DraftKings"}
    return {
        "bookmaker_key": key,
        "canonical_bookmaker": names[key],
        "bookmaker_last_update": (COLLECTED - timedelta(minutes=age)).isoformat(),
        "market_key": "spreads",
        "home_team": "SF",
        "home_points": home_points,
        "home_price": home_price,
        "away_team": "SEA",
        "away_points": away_points,
        "away_price": away_price,
    }


def observation(
    books: list[dict[str, object]] | None = None,
    *,
    collected_at: datetime = COLLECTED,
) -> dict[str, object]:
    return build_spread_observation(
        game(),
        books or [book("betmgm"), book("fanduel"), book("draftkings")],
        collected_at=collected_at,
        target_label="T1H",
        provider="the-odds-api",
        provider_event_id="provider-event-1",
        raw_response_id=RAW_ID,
        raw_payload_sha256=PAYLOAD_SHA,
        parser_version="step92b-v1",
    )


def reidentify(row: dict[str, object]) -> dict[str, object]:
    material = deepcopy(row)
    material.pop("observation_id", None)
    material["observation_id"] = hashlib.sha256(canonical_json(material).encode()).hexdigest()
    return material


def test_valid_three_book_quote_preserves_atomic_point_and_price() -> None:
    row = observation(
        [
            book("betmgm", home_price=-110, away_price=-110),
            book("fanduel", home_price=-105, away_price=-115, age=3),
            book("draftkings", home_price=100, away_price=-120, age=4),
        ]
    )
    validate_spread_observation(row)
    assert tuple(item["bookmaker_key"] for item in row["books"]) == BOOK_KEYS
    assert row["books"][2]["home_points"] == -3.5
    assert row["books"][2]["home_price"] == 100


def test_books_may_have_different_internally_opposing_main_lines() -> None:
    row = observation(
        [book("betmgm", -2.5, 2.5), book("fanduel", -3.0, 3.0), book("draftkings")]
    )
    assert [item["home_points"] for item in row["books"]] == [-2.5, -3.0, -3.5]


def test_positive_home_spread_and_plus_money_price_are_valid() -> None:
    row = observation([book(key, 2.0, -2.0, 105, -125) for key in BOOK_KEYS])
    assert row["books"][0]["home_points"] == 2.0
    assert row["books"][0]["home_price"] == 105


def test_pickem_and_negative_zero_have_one_canonical_identity() -> None:
    positive = observation([book(key, 0.0, 0.0) for key in BOOK_KEYS])
    negative = observation([book(key, -0.0, -0.0) for key in BOOK_KEYS])
    assert positive == negative
    assert all(item["home_points"] == 0.0 for item in negative["books"])
    assert all(str(item["home_points"]) == "0.0" for item in negative["books"])


def test_dictionary_and_input_book_order_do_not_change_identity() -> None:
    baseline = observation()
    reversed_fields = [dict(reversed(tuple(item.items()))) for item in reversed([book(key) for key in BOOK_KEYS])]
    assert observation(reversed_fields)["observation_id"] == baseline["observation_id"]


def test_semantic_changes_change_identity() -> None:
    baseline = observation()
    variants = [
        observation([book("betmgm", -3.0, 3.0), book("fanduel"), book("draftkings")]),
        observation([book("betmgm", home_price=-105), book("fanduel"), book("draftkings")]),
        observation([book("betmgm", age=3), book("fanduel"), book("draftkings")]),
        observation(collected_at=COLLECTED + timedelta(minutes=1)),
    ]
    assert all(item["observation_id"] != baseline["observation_id"] for item in variants)


@pytest.mark.parametrize("home,away", [(-3.5, 2.5), (-3.0, 3.5)])
def test_nonopposing_spreads_reject(home: float, away: float) -> None:
    with pytest.raises(OperationalSpreadError, match="exact opposites"):
        observation([book("betmgm", home, away), book("fanduel"), book("draftkings")])


@pytest.mark.parametrize("points", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_points_reject(points: float) -> None:
    with pytest.raises(OperationalSpreadError, match="finite"):
        observation([book("betmgm", points, -3.5), book("fanduel"), book("draftkings")])


@pytest.mark.parametrize("price", [0, 50, -50, "garbage", float("nan"), float("inf")])
def test_invalid_american_prices_reject(price: object) -> None:
    with pytest.raises(OperationalSpreadError, match="American odds|<= -100"):
        observation([book("betmgm", home_price=price), book("fanduel"), book("draftkings")])  # type: ignore[arg-type]


@pytest.mark.parametrize("price", [-110, -105, 100, 105, 210])
def test_supported_american_price_boundaries(price: int) -> None:
    assert observation([book(key, home_price=price) for key in BOOK_KEYS])["books"][0]["home_price"] == price


def test_missing_duplicate_and_unknown_books_reject() -> None:
    with pytest.raises(OperationalSpreadError, match="three required"):
        observation([book("betmgm"), book("fanduel")])
    with pytest.raises(OperationalSpreadError, match="duplicate"):
        observation([book("betmgm"), book("betmgm"), book("draftkings")])
    unknown = book("betmgm")
    unknown["bookmaker_key"] = "unknown"
    with pytest.raises(OperationalSpreadError, match="three required"):
        observation([unknown, book("fanduel"), book("draftkings")])


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("market_key", "alternate_spreads", "market_key"),
        ("home_team", "SEA", "team identity"),
        ("away_team", "OTHER", "team identity"),
        ("home_price", None, "American odds"),
    ],
)
def test_market_team_and_missing_price_fail_closed(field: str, value: object, match: str) -> None:
    malformed = book("betmgm")
    malformed[field] = value
    with pytest.raises(OperationalSpreadError, match=match):
        observation([malformed, book("fanduel"), book("draftkings")])


def test_duplicate_or_missing_outcome_shape_and_alternate_ambiguity_reject() -> None:
    for extra in (
        {"outcomes": [{"name": "SF"}, {"name": "SF"}]},
        {"markets": ["main", "alternate"]},
    ):
        malformed = {**book("betmgm"), **extra}
        with pytest.raises(OperationalSpreadError, match="schema"):
            observation([malformed, book("fanduel"), book("draftkings")])
    missing = book("betmgm")
    missing.pop("away_team")
    with pytest.raises(OperationalSpreadError, match="schema"):
        observation([missing, book("fanduel"), book("draftkings")])


def test_future_and_stale_bookmaker_timestamps_reject() -> None:
    future = book("betmgm")
    future["bookmaker_last_update"] = (COLLECTED + timedelta(seconds=1)).isoformat()
    with pytest.raises(OperationalSpreadError, match="after collection"):
        observation([future, book("fanduel"), book("draftkings")])
    with pytest.raises(OperationalSpreadError, match="stale"):
        observation([book("betmgm", age=11), book("fanduel"), book("draftkings")])


@pytest.mark.parametrize("minutes", [0, -1, 44, 76])
def test_kickoff_and_target_window_boundaries_fail_closed(minutes: int) -> None:
    with pytest.raises(OperationalSpreadError, match="pre-kickoff|outside target"):
        observation(collected_at=KICKOFF - timedelta(minutes=minutes))


def test_invalid_target_and_raw_linkage_reject() -> None:
    with pytest.raises(OperationalSpreadError, match="target label"):
        build_spread_observation(
            game(), [book(key) for key in BOOK_KEYS], collected_at=COLLECTED,
            target_label="OTHER", provider="the-odds-api", raw_response_id=RAW_ID,
            raw_payload_sha256=PAYLOAD_SHA, parser_version="step92b-v1",
        )
    with pytest.raises(OperationalSpreadError, match="raw_response_id"):
        build_spread_observation(
            game(), [book(key) for key in BOOK_KEYS], collected_at=COLLECTED,
            target_label="T1H", provider="the-odds-api", raw_response_id="bad",
            raw_payload_sha256=PAYLOAD_SHA, parser_version="step92b-v1",
        )


def test_append_is_exactly_idempotent_and_conflicts_fail_closed(tmp_path) -> None:
    path = tmp_path / "spreads.jsonl"
    row = observation()
    assert append_spread_observation(path, row) is True
    assert append_spread_observation(path, row) is False
    assert read_spread_history(path) == (row,)
    conflict = observation([book("betmgm", -3.0, 3.0), book("fanduel"), book("draftkings")])
    with pytest.raises(ImmutableSpreadConflictError):
        append_spread_observation(path, conflict)


def test_conflicting_claimed_identity_is_rejected() -> None:
    row = observation()
    row["books"][0]["home_price"] = -105
    with pytest.raises(OperationalSpreadError, match="identity"):
        validate_spread_observation(row)
        append_spread_observation("unused", row)


def test_noncanonical_negative_zero_in_persisted_payload_rejects() -> None:
    row = observation([book(key, 0.0, 0.0) for key in BOOK_KEYS])
    row["books"][0]["home_points"] = -0.0
    row = reidentify(row)
    with pytest.raises(OperationalSpreadError, match="negative zero"):
        validate_spread_observation(row)
