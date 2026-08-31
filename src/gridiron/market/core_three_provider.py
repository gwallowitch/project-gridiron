"""Strict one-response normalization for the inactive Core-Three protocol."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from gridiron.market.core_three_types import (
    BOOK_KEYS,
    CANONICAL_BOOKS,
    MARKET_KEYS,
    PROTOCOL_ID,
    AtomicObservation,
    Book,
    CoreThreeError,
    Market,
    Outcome,
    validate_identity,
    validate_jurisdiction,
    validate_safe_strings,
)

MAX_QUOTE_AGE = timedelta(minutes=10)
CAPTURE_WINDOW_MINUTES = (55, 65)


def parse_timestamp(value: object, field: str) -> datetime:
    """Parse an explicit ISO-8601 timestamp and normalize it to UTC."""
    if not isinstance(value, str) or not value:
        raise CoreThreeError(f"{field}: INVALID_TIMESTAMP")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise CoreThreeError(f"{field}: INVALID_TIMESTAMP") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CoreThreeError(f"{field}: TIMEZONE_REQUIRED")
    return parsed.astimezone(UTC)


def normalize_event_response(
    response: Mapping[str, Any],
    authoritative_event: Mapping[str, Any],
    *,
    receipt_at: str,
    timestamp_semantics_approved: bool,
    jurisdiction: str = "US_AGGREGATE",
    response_id: str | None = None,
) -> AtomicObservation:
    """Validate one provider response; never persist its raw representation."""
    if timestamp_semantics_approved is not True:
        raise CoreThreeError("TIMESTAMP_SEMANTICS_UNAPPROVED")
    response = deepcopy(dict(response))
    authoritative_event = deepcopy(dict(authoritative_event))
    validate_safe_strings(response)
    validate_safe_strings(authoritative_event)
    validate_jurisdiction(jurisdiction)
    if response.get("sport_key", "americanfootball_nfl") != "americanfootball_nfl":
        raise CoreThreeError("SPORT_MISMATCH")
    try:
        digest = hashlib.sha256(
            json.dumps(
                response, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        ).hexdigest()
    except (TypeError, ValueError) as exc:
        raise CoreThreeError("MALFORMED_RESPONSE") from exc
    # The fallback is a content identity, not an authenticated acquisition-attempt ID.
    acquisition_id = _string(
        digest if response_id is None else response_id, "response_id"
    )
    _validate_acquisition(response, acquisition_id, receipt_at)
    receipt = parse_timestamp(receipt_at, "receipt_at")
    provider_id = _string(response.get("id"), "event.id")
    expected_provider_id = _string(
        authoritative_event.get("provider_event_id"), "provider_event_id"
    )
    if provider_id != expected_provider_id:
        raise CoreThreeError("EVENT_ID_MISMATCH")
    home = _string(response.get("home_team"), "event.home_team")
    away = _string(response.get("away_team"), "event.away_team")
    if home != authoritative_event.get("home_team"):
        raise CoreThreeError("HOME_TEAM_MISMATCH")
    if away != authoritative_event.get("away_team"):
        raise CoreThreeError("AWAY_TEAM_MISMATCH")
    kickoff = parse_timestamp(response.get("commence_time"), "event.commence_time")
    authoritative_kickoff = parse_timestamp(
        authoritative_event.get("kickoff_at"), "authoritative.kickoff_at"
    )
    if kickoff != authoritative_kickoff:
        raise CoreThreeError("KICKOFF_MISMATCH")
    minutes_to_kickoff = (kickoff - receipt).total_seconds() / 60
    if not CAPTURE_WINDOW_MINUTES[0] <= minutes_to_kickoff <= CAPTURE_WINDOW_MINUTES[1]:
        raise CoreThreeError("OUTSIDE_CAPTURE_WINDOW")

    raw_books = response.get("bookmakers")
    if not isinstance(raw_books, list):
        raise CoreThreeError("BOOKMAKERS_MALFORMED")
    keys = [
        _string(item.get("key"), "book.key")
        for item in raw_books
        if isinstance(item, Mapping)
    ]
    if len(keys) != len(raw_books):
        raise CoreThreeError("BOOKMAKER_MALFORMED")
    if len(keys) != len(set(keys)):
        raise CoreThreeError("DUPLICATE_BOOKMAKER")
    if set(keys) != set(BOOK_KEYS):
        raise CoreThreeError("BOOK_UNIVERSE_MISMATCH")
    normalized = {
        item["key"]: _normalize_book(item, home=home, away=away, receipt=receipt)
        for item in raw_books
    }
    return AtomicObservation(
        protocol_id=PROTOCOL_ID,
        provider="The Odds API",
        provider_event_id=provider_id,
        authoritative_game_id=_string(authoritative_event.get("game_id"), "game_id"),
        home_team=home,
        away_team=away,
        kickoff_at=kickoff,
        receipt_at=receipt,
        jurisdiction=jurisdiction,
        books=tuple(normalized[key] for key in BOOK_KEYS),
        response_id=acquisition_id,
        response_digest=digest,
        receipt_at_text=receipt_at,
    )


def assert_external_gates(
    *,
    timestamp_semantics_approved: bool,
    jurisdiction_approved: bool,
    draftkings_execution_state_approved: bool,
    retention_approved: bool,
    authoritative_kickoff_approved: bool,
    governance_approved: bool,
    effective_timestamp: str | None,
) -> None:
    """Check caller assertions only; never authenticate or authorize activation."""
    gates = {
        "TIMESTAMP_SEMANTICS_UNAPPROVED": timestamp_semantics_approved,
        "JURISDICTION_UNAPPROVED": jurisdiction_approved,
        "DRAFTKINGS_EXECUTION_STATE_UNAPPROVED": draftkings_execution_state_approved,
        "RETENTION_UNAPPROVED": retention_approved,
        "AUTHORITATIVE_KICKOFF_UNAPPROVED": authoritative_kickoff_approved,
        "GOVERNANCE_UNAPPROVED": governance_approved,
        "EFFECTIVE_TIMESTAMP_MISSING": effective_timestamp is not None,
    }
    failed = [name for name, passed in gates.items() if passed is not True]
    if failed:
        raise CoreThreeError("EXTERNAL_GATES_BLOCKED: " + ",".join(failed))
    parse_timestamp(effective_timestamp, "effective_timestamp")
    raise CoreThreeError(
        "EXTERNAL_AUTHORIZATION_NOT_AUTHENTICATED_ACTIVATION_PROHIBITED"
    )


def _normalize_book(
    raw: Mapping[str, Any], *, home: str, away: str, receipt: datetime
) -> Book:
    _validate_availability(raw)
    key = raw.get("key")
    if key not in BOOK_KEYS:
        raise CoreThreeError("UNKNOWN_BOOKMAKER")
    markets = raw.get("markets")
    if not isinstance(markets, list):
        raise CoreThreeError(f"{key}: MARKETS_MALFORMED")
    market_keys = [
        _string(item.get("key"), "market.key")
        for item in markets
        if isinstance(item, Mapping)
    ]
    if len(market_keys) != len(markets):
        raise CoreThreeError(f"{key}: MARKET_MALFORMED")
    if len(market_keys) != len(set(market_keys)):
        raise CoreThreeError(f"{key}: DUPLICATE_MARKET")
    if set(market_keys) != set(MARKET_KEYS):
        raise CoreThreeError(f"{key}: MARKET_UNIVERSE_MISMATCH")
    by_key = {
        item["key"]: _normalize_market(
            item, book_key=key, home=home, away=away, receipt=receipt
        )
        for item in markets
    }
    return Book(
        key=key,
        canonical_name=CANONICAL_BOOKS[key],
        sid=_optional_string(raw.get("sid"), f"{key}.sid"),
        markets=tuple(by_key[market_key] for market_key in MARKET_KEYS),
    )


def _normalize_market(
    raw: Mapping[str, Any],
    *,
    book_key: str,
    home: str,
    away: str,
    receipt: datetime,
) -> Market:
    market_key = raw.get("key")
    if market_key not in MARKET_KEYS:
        raise CoreThreeError(f"{book_key}: ALTERNATE_OR_UNKNOWN_MARKET")
    _validate_availability(raw)
    timestamp_text = _string(raw.get("last_update"), "last_update")
    updated = parse_timestamp(timestamp_text, f"{book_key}.{market_key}.last_update")
    if updated > receipt:
        raise CoreThreeError(f"{book_key}.{market_key}: FUTURE_QUOTE")
    if receipt - updated > MAX_QUOTE_AGE:
        raise CoreThreeError(f"{book_key}.{market_key}: STALE_QUOTE")
    raw_outcomes = raw.get("outcomes")
    if not isinstance(raw_outcomes, list) or len(raw_outcomes) != 2:
        raise CoreThreeError(f"{book_key}.{market_key}: INCOMPLETE_OUTCOMES")
    outcomes = tuple(
        _normalize_outcome(item, f"{book_key}.{market_key}") for item in raw_outcomes
    )
    names = [item.name for item in outcomes]
    if len(set(names)) != 2:
        raise CoreThreeError(f"{book_key}.{market_key}: DUPLICATE_OUTCOME")
    if market_key in {"h2h", "spreads"} and set(names) != {home, away}:
        raise CoreThreeError(f"{book_key}.{market_key}: TEAM_OUTCOME_MISMATCH")
    if market_key == "h2h" and any(item.point is not None for item in outcomes):
        raise CoreThreeError(f"{book_key}.h2h: UNEXPECTED_POINT")
    if market_key == "spreads":
        points = [item.point for item in outcomes]
        if any(point is None for point in points) or points[0] != -points[1]:
            raise CoreThreeError(f"{book_key}.spreads: CONFLICTING_LINE")
    if market_key == "totals":
        if set(names) != {"Over", "Under"}:
            raise CoreThreeError(f"{book_key}.totals: OUTCOME_MISMATCH")
        points = [item.point for item in outcomes]
        if any(point is None for point in points) or points[0] != points[1]:
            raise CoreThreeError(f"{book_key}.totals: CONFLICTING_LINE")
    return Market(
        key=market_key,
        last_update_text=timestamp_text,
        last_update=updated,
        outcomes=outcomes,  # type: ignore[arg-type]
    )


def _normalize_outcome(raw: object, field: str) -> Outcome:
    if not isinstance(raw, Mapping):
        raise CoreThreeError(f"{field}: MALFORMED_OUTCOME")
    _validate_availability(raw)
    name = _string(raw.get("name"), f"{field}.name")
    price = raw.get("price")
    if isinstance(price, bool) or not isinstance(price, int) or -100 < price < 100:
        raise CoreThreeError(f"{field}.{name}: MALFORMED_PRICE")
    point = raw.get("point")
    if point is not None and (
        isinstance(point, bool)
        or not isinstance(point, (int, float))
        or not math.isfinite(float(point))
    ):
        raise CoreThreeError(f"{field}.{name}: MALFORMED_POINT")
    return Outcome(
        name=name,
        price=price,
        point=float(point) if point is not None else None,
        sid=_optional_string(raw.get("sid"), f"{field}.{name}.sid"),
    )


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CoreThreeError(f"{field}: NONEMPTY_STRING_REQUIRED")
    validate_safe_strings(value)
    return value


def _validate_availability(raw: Mapping[str, Any]) -> None:
    for key in ("suspended", "locked", "active"):
        if key not in raw:
            continue
        if type(raw[key]) is not bool:
            raise CoreThreeError("MALFORMED_AVAILABILITY")
        if raw[key] is (key != "active"):
            raise CoreThreeError("SUSPENDED_MARKET_OR_UNAVAILABLE_COMPONENT")


def _validate_acquisition(value: Any, response_id: str, receipt_at: str) -> None:
    """Reject conflicting supplied component provenance; not origin authentication."""
    if isinstance(value, dict):
        validate_identity(value)
        if "response_id" in value and value["response_id"] != response_id:
            raise CoreThreeError("RESPONSE_IDENTITY_MISMATCH")
        if "receipt_at" in value and parse_timestamp(
            value["receipt_at"], "receipt_at"
        ) != (parse_timestamp(receipt_at, "receipt_at")):
            raise CoreThreeError("RESPONSE_RECEIPT_MISMATCH")
        for item in value.values():
            _validate_acquisition(item, response_id, receipt_at)
    elif isinstance(value, list):
        for item in value:
            _validate_acquisition(item, response_id, receipt_at)


def _optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _string(value, field)
