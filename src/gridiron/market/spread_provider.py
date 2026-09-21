"""Offline provider-shaped payload parser for Step 92C spread evidence."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from gridiron.market.operational_spreads import (
    BOOKS,
    OperationalSpreadError,
    build_spread_observation,
    parse_timestamp,
)

PARSER_VERSION = "step92c-v1"


class SpreadParseError(ValueError):
    """A sanitized deterministic parser failure safe for attempt metadata."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def _fail(code: str) -> None:
    raise SpreadParseError(code)


def _map_contract_error(exc: OperationalSpreadError) -> str:
    text = str(exc).lower()
    if "exact opposites" in text:
        return "CONFLICTING_SPREAD"
    if "stale" in text:
        return "STALE_QUOTE"
    if (
        "timestamp" in text
        or "timezone" in text
        or "pre-kickoff" in text
        or "outside target" in text
    ):
        return "TIMESTAMP_INVALID"
    if "team identity" in text or "game identity" in text:
        return "IDENTITY_MISMATCH"
    return "MALFORMED_MARKET"


def parse_spread_event(
    payload: object,
    expected_game: Mapping[str, Any],
    *,
    collected_at: datetime,
    target_label: str,
    raw_response_id: str,
    raw_payload_sha256: str,
    expected_provider_event_id: str | None = None,
    provider: str = "the-odds-api",
) -> dict[str, Any]:
    """Normalize exactly one supplied event without performing any I/O."""
    if not isinstance(payload, Mapping):
        _fail("MISSING_GAME" if payload is None else "MALFORMED_MARKET")
    if collected_at.tzinfo is None:
        _fail("TIMESTAMP_INVALID")
    required_game = {
        "game_id", "season", "week", "season_type", "home_team", "away_team",
        "kickoff_at",
    }
    if set(expected_game) != required_game:
        _fail("IDENTITY_MISMATCH")
    event_id = payload.get("id")
    if not isinstance(event_id, str) or not event_id:
        _fail("IDENTITY_MISMATCH")
    if expected_provider_event_id is not None and event_id != expected_provider_event_id:
        _fail("IDENTITY_MISMATCH")
    if (
        payload.get("home_team") != expected_game["home_team"]
        or payload.get("away_team") != expected_game["away_team"]
    ):
        _fail("IDENTITY_MISMATCH")
    try:
        provider_kickoff = parse_timestamp(payload.get("commence_time"), "commence_time")
        expected_kickoff = parse_timestamp(expected_game["kickoff_at"], "kickoff_at")
    except OperationalSpreadError:
        _fail("TIMESTAMP_INVALID")
    if provider_kickoff != expected_kickoff:
        _fail("IDENTITY_MISMATCH")
    raw_books = payload.get("bookmakers")
    if not isinstance(raw_books, list):
        _fail("MALFORMED_MARKET")
    selected: dict[str, Mapping[str, Any]] = {}
    for raw_book in raw_books:
        if not isinstance(raw_book, Mapping):
            _fail("MALFORMED_MARKET")
        key = raw_book.get("key")
        if key not in BOOKS:
            continue
        if key in selected:
            _fail("MALFORMED_MARKET")
        selected[str(key)] = raw_book
    if set(selected) != set(BOOKS):
        _fail("MISSING_BOOK")
    parsed_books: list[dict[str, Any]] = []
    for key in BOOKS:
        raw_book = selected[key]
        markets = raw_book.get("markets")
        if not isinstance(markets, list):
            _fail("MISSING_MARKET")
        spreads = [
            market for market in markets
            if isinstance(market, Mapping) and market.get("key") == "spreads"
        ]
        if not spreads:
            _fail("MISSING_MARKET")
        if len(spreads) != 1:
            _fail("MALFORMED_MARKET")
        market = spreads[0]
        outcomes = market.get("outcomes")
        if not isinstance(outcomes, list) or len(outcomes) != 2:
            _fail("MALFORMED_MARKET")
        if not all(isinstance(item, Mapping) for item in outcomes):
            _fail("MALFORMED_MARKET")
        names = [item.get("name") for item in outcomes]
        if len(set(names)) != 2:
            _fail("MALFORMED_MARKET")
        by_name = {item.get("name"): item for item in outcomes}
        if set(by_name) != {
            expected_game["home_team"], expected_game["away_team"]
        }:
            _fail("IDENTITY_MISMATCH")
        home = by_name[expected_game["home_team"]]
        away = by_name[expected_game["away_team"]]
        # Core-Three gives a market timestamp precedence; bookmaker time is the
        # documented fallback when a market timestamp is absent.
        last_update = market.get("last_update", raw_book.get("last_update"))
        parsed_books.append(
            {
                "bookmaker_key": key,
                "canonical_bookmaker": BOOKS[key],
                "bookmaker_last_update": last_update,
                "market_key": "spreads",
                "home_team": expected_game["home_team"],
                "home_points": home.get("point"),
                "home_price": home.get("price"),
                "away_team": expected_game["away_team"],
                "away_points": away.get("point"),
                "away_price": away.get("price"),
            }
        )
    try:
        return build_spread_observation(
            expected_game,
            parsed_books,
            collected_at=collected_at,
            target_label=target_label,
            provider=provider,
            provider_event_id=event_id,
            raw_response_id=raw_response_id,
            raw_payload_sha256=raw_payload_sha256,
            parser_version=PARSER_VERSION,
        )
    except OperationalSpreadError as exc:
        raise SpreadParseError(_map_contract_error(exc)) from None
