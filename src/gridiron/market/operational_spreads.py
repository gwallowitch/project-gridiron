"""Immutable non-prospective Step 92B spread observation contract."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gridiron.market.operational_history import canonical_json

SCHEMA_VERSION = 1
RECORD_TYPE = "OPERATIONAL_SPREAD_MARKET_OBSERVATION"
CLASSIFICATION = "NON_PROSPECTIVE_SPREAD_MARKET_OBSERVATION"
MARKET_KEY = "spreads"
LANE = "SPREAD"
BOOKS = {"betmgm": "BetMGM", "fanduel": "FanDuel", "draftkings": "DraftKings"}
BOOK_KEYS = tuple(BOOKS)
TARGET_WINDOWS = {
    "T12H": (720, 660, 780),
    "T6H": (360, 330, 390),
    "T3H": (180, 150, 210),
    "T1H": (60, 45, 75),
    "NEAR_KICKOFF": (15, 5, 30),
}
MAX_QUOTE_AGE_MINUTES = 10.0
_HEX_64 = re.compile(r"[0-9a-f]{64}")


class OperationalSpreadError(ValueError):
    """Spread evidence violates the immutable Step 92B contract."""


class ImmutableSpreadConflictError(OperationalSpreadError):
    """An immutable game/target identity already has different content."""


def parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise OperationalSpreadError(f"{field} must be an ISO-8601 timestamp")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise OperationalSpreadError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OperationalSpreadError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OperationalSpreadError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise OperationalSpreadError(f"{field} must be finite")
    return result


def _canonical_point(value: object, field: str) -> float:
    point = _number(value, field)
    return 0.0 if point == 0.0 else point


def _price(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OperationalSpreadError(f"{field} must be integer American odds")
    if not math.isfinite(float(value)) or int(value) != value:
        raise OperationalSpreadError(f"{field} must be integer American odds")
    result = int(value)
    if -100 < result < 100:
        raise OperationalSpreadError(f"{field} must be <= -100 or >= +100")
    return result


def _nonempty(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise OperationalSpreadError(f"{field} must be a nonempty string")
    return value


def _digest(value: object, field: str) -> str:
    text = _nonempty(value, field)
    if _HEX_64.fullmatch(text) is None:
        raise OperationalSpreadError(f"{field} must be a lowercase SHA-256 identity")
    return text


def _validate_game(game: object) -> Mapping[str, Any]:
    fields = {
        "game_id", "season", "week", "season_type", "home_team", "away_team",
        "kickoff_at",
    }
    if not isinstance(game, Mapping) or set(game) != fields:
        raise OperationalSpreadError("invalid canonical game schema")
    if (
        not isinstance(game["game_id"], str)
        or not game["game_id"]
        or game["season"] != 2026
        or isinstance(game["week"], bool)
        or not isinstance(game["week"], int)
        or not 1 <= game["week"] <= 18
        or game["season_type"] != "REG"
        or not isinstance(game["home_team"], str)
        or not game["home_team"]
        or not isinstance(game["away_team"], str)
        or not game["away_team"]
        or game["home_team"] == game["away_team"]
    ):
        raise OperationalSpreadError("invalid canonical 2026 game identity")
    parse_timestamp(game["kickoff_at"], "kickoff_at")
    return game


def _validate_book(
    book: object, *, game: Mapping[str, Any], collected: datetime
) -> str:
    fields = {
        "bookmaker_key", "canonical_bookmaker", "bookmaker_last_update",
        "market_key", "home_team", "home_points", "home_price", "away_team",
        "away_points", "away_price",
    }
    if not isinstance(book, Mapping) or set(book) != fields:
        raise OperationalSpreadError("invalid spread book schema")
    key = book.get("bookmaker_key")
    if key not in BOOKS or book.get("canonical_bookmaker") != BOOKS[key]:
        raise OperationalSpreadError("unknown or misidentified spread bookmaker")
    if book.get("market_key") != MARKET_KEY:
        raise OperationalSpreadError("spread market_key must be spreads")
    if (
        book.get("home_team") != game["home_team"]
        or book.get("away_team") != game["away_team"]
    ):
        raise OperationalSpreadError("spread outcome team identity mismatch")
    home = _canonical_point(book.get("home_points"), f"{key}.home_points")
    away = _canonical_point(book.get("away_points"), f"{key}.away_points")
    for stored, normalized in (
        (book.get("home_points"), home), (book.get("away_points"), away)
    ):
        if float(stored) == 0.0 and math.copysign(1.0, float(stored)) < 0:
            raise OperationalSpreadError("negative zero is not canonical")
        if float(stored) != normalized:
            raise OperationalSpreadError("spread point is not canonical")
    if away != -home:
        raise OperationalSpreadError("spread points must be exact opposites")
    _price(book.get("home_price"), f"{key}.home_price")
    _price(book.get("away_price"), f"{key}.away_price")
    updated = parse_timestamp(book.get("bookmaker_last_update"), f"{key}.last_update")
    age = (collected - updated).total_seconds() / 60.0
    if age < 0:
        raise OperationalSpreadError("bookmaker timestamp is after collection")
    if age > MAX_QUOTE_AGE_MINUTES:
        raise OperationalSpreadError("spread quote is stale")
    return str(key)


def validate_spread_observation(record: Mapping[str, Any]) -> None:
    fields = {
        "schema_version", "record_type", "classification", "prospective_evidence",
        "lane", "game", "timing", "provider", "provider_event_id",
        "raw_response_id", "raw_payload_sha256", "parser_version", "books",
    }
    if set(record) not in (fields, fields | {"observation_id"}):
        raise OperationalSpreadError("spread fields do not match immutable schema")
    if (
        record.get("schema_version") != SCHEMA_VERSION
        or record.get("record_type") != RECORD_TYPE
        or record.get("classification") != CLASSIFICATION
        or record.get("prospective_evidence") is not False
        or record.get("lane") != LANE
    ):
        raise OperationalSpreadError("invalid spread observation identity")
    game = _validate_game(record.get("game"))
    timing = record.get("timing")
    timing_fields = {
        "target_label", "target_minutes", "collected_at", "minutes_before_kickoff",
        "target_deviation_minutes",
    }
    if not isinstance(timing, Mapping) or set(timing) != timing_fields:
        raise OperationalSpreadError("invalid spread timing schema")
    target = timing.get("target_label")
    if target not in TARGET_WINDOWS:
        raise OperationalSpreadError("invalid spread target label")
    target_minutes, low, high = TARGET_WINDOWS[str(target)]
    if timing.get("target_minutes") != target_minutes:
        raise OperationalSpreadError("spread target minutes are inconsistent")
    kickoff = parse_timestamp(game["kickoff_at"], "kickoff_at")
    collected = parse_timestamp(timing.get("collected_at"), "collected_at")
    actual = _number(timing.get("minutes_before_kickoff"), "minutes_before_kickoff")
    expected = (kickoff - collected).total_seconds() / 60.0
    if actual <= 0 or not math.isclose(actual, expected, abs_tol=1e-12):
        raise OperationalSpreadError("spread observation must be strictly pre-kickoff")
    if not low <= actual <= high:
        raise OperationalSpreadError("spread observation is outside target window")
    deviation = _number(timing.get("target_deviation_minutes"), "target deviation")
    if not math.isclose(deviation, actual - target_minutes, abs_tol=1e-12):
        raise OperationalSpreadError("spread target deviation is inconsistent")
    _nonempty(record.get("provider"), "provider")
    provider_event = record.get("provider_event_id")
    if provider_event is not None:
        _nonempty(provider_event, "provider_event_id")
    _digest(record.get("raw_response_id"), "raw_response_id")
    _digest(record.get("raw_payload_sha256"), "raw_payload_sha256")
    _nonempty(record.get("parser_version"), "parser_version")
    books = record.get("books")
    if not isinstance(books, list) or len(books) != len(BOOKS):
        raise OperationalSpreadError("exactly three spread books are required")
    keys = tuple(_validate_book(book, game=game, collected=collected) for book in books)
    if keys != BOOK_KEYS:
        raise OperationalSpreadError("spread books must be unique and canonically ordered")


def build_spread_observation(
    game: Mapping[str, Any],
    books: Sequence[Mapping[str, Any]],
    *,
    collected_at: datetime,
    target_label: str,
    provider: str,
    raw_response_id: str,
    raw_payload_sha256: str,
    parser_version: str,
    provider_event_id: str | None = None,
) -> dict[str, Any]:
    game = _validate_game(game)
    if collected_at.tzinfo is None:
        raise OperationalSpreadError("collected_at must include a timezone")
    collected = collected_at.astimezone(UTC)
    kickoff = parse_timestamp(game["kickoff_at"], "kickoff_at")
    if target_label not in TARGET_WINDOWS:
        raise OperationalSpreadError("invalid spread target label")
    target_minutes = TARGET_WINDOWS[target_label][0]
    by_key: dict[str, Mapping[str, Any]] = {}
    for book in books:
        if not isinstance(book, Mapping):
            raise OperationalSpreadError("invalid spread book schema")
        key = book.get("bookmaker_key")
        if not isinstance(key, str) or key in by_key:
            raise OperationalSpreadError("duplicate or invalid spread bookmaker")
        by_key[key] = book
    if set(by_key) != set(BOOK_KEYS):
        raise OperationalSpreadError("exactly the three required spread books are required")
    normalized_books = []
    for key in BOOK_KEYS:
        book = by_key[key]
        normalized_books.append(
            {
                **dict(book),
                "home_points": _canonical_point(book.get("home_points"), f"{key}.home_points"),
                "away_points": _canonical_point(book.get("away_points"), f"{key}.away_points"),
                "home_price": _price(book.get("home_price"), f"{key}.home_price"),
                "away_price": _price(book.get("away_price"), f"{key}.away_price"),
                "bookmaker_last_update": _utc_text(
                    parse_timestamp(book.get("bookmaker_last_update"), f"{key}.last_update")
                ),
            }
        )
    actual = (kickoff - collected).total_seconds() / 60.0
    base = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "classification": CLASSIFICATION,
        "prospective_evidence": False,
        "lane": LANE,
        "game": {**dict(game), "kickoff_at": _utc_text(kickoff)},
        "timing": {
            "target_label": target_label,
            "target_minutes": target_minutes,
            "collected_at": _utc_text(collected),
            "minutes_before_kickoff": actual,
            "target_deviation_minutes": actual - target_minutes,
        },
        "provider": provider,
        "provider_event_id": provider_event_id,
        "raw_response_id": raw_response_id,
        "raw_payload_sha256": raw_payload_sha256,
        "parser_version": parser_version,
        "books": normalized_books,
    }
    validate_spread_observation(base)
    return {**base, "observation_id": hashlib.sha256(canonical_json(base).encode()).hexdigest()}


def _validated_identity(record: Mapping[str, Any]) -> str:
    validate_spread_observation(record)
    material = dict(record)
    identity = material.pop("observation_id", None)
    expected = hashlib.sha256(canonical_json(material).encode()).hexdigest()
    if identity != expected:
        raise OperationalSpreadError("invalid spread observation identity")
    return str(identity)


def read_spread_history(path: Path | str) -> tuple[dict[str, Any], ...]:
    source = Path(path)
    if not source.exists():
        return ()
    rows: list[dict[str, Any]] = []
    slots: dict[tuple[str, str], dict[str, Any]] = {}
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise OperationalSpreadError(f"blank spread line {number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise OperationalSpreadError(f"invalid spread JSON at line {number}") from exc
        if not isinstance(row, dict):
            raise OperationalSpreadError(f"spread line {number} is not an object")
        _validated_identity(row)
        slot = (row["game"]["game_id"], row["timing"]["target_label"])
        existing = slots.get(slot)
        if existing is not None and existing != row:
            raise ImmutableSpreadConflictError("conflicting immutable spread target")
        if existing is None:
            slots[slot] = row
            rows.append(row)
    return tuple(rows)


def append_spread_observation(path: Path | str, record: Mapping[str, Any]) -> bool:
    """Append a new target; return False for an exact idempotent replay."""
    _validated_identity(record)
    slot = (record["game"]["game_id"], record["timing"]["target_label"])
    for existing in read_spread_history(path):
        if (existing["game"]["game_id"], existing["timing"]["target_label"]) == slot:
            if existing == dict(record):
                return False
            raise ImmutableSpreadConflictError("conflicting immutable spread target")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return True
