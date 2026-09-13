"""Fail-closed non-prospective operational NFL totals observations."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
RECORD_TYPE = "OPERATIONAL_TOTALS_MARKET_OBSERVATION"
CLASSIFICATION = "NON_PROSPECTIVE_TOTALS_MARKET_OBSERVATION"
BOOKS = {"betmgm": "BetMGM", "fanduel": "FanDuel", "draftkings": "DraftKings"}
TARGET_WINDOWS = {
    "T12H": (720, 660, 780),
    "T6H": (360, 330, 390),
    "T3H": (180, 150, 210),
    "T1H": (60, 45, 75),
    "NEAR_KICKOFF": (15, 5, 30),
}
AUTOMATIC_PROVIDER_PREFIX = "the-odds-api-operational-totals-step91r:"
MANUAL_PROVIDER = "manual-totals-observation"
MAX_QUOTE_AGE_MINUTES = 10.0


class OperationalTotalsError(ValueError):
    """Totals input or retained history violates the immutable contract."""


class DuplicateTotalsObservationError(OperationalTotalsError):
    """A duplicate automatic game/target observation already exists."""


def canonical_json(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise OperationalTotalsError("totals record is not canonical JSON") from exc


def parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise OperationalTotalsError(f"{field} must be an ISO-8601 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise OperationalTotalsError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise OperationalTotalsError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OperationalTotalsError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise OperationalTotalsError(f"{field} must be finite")
    return result


def _price(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
        raise OperationalTotalsError(f"{field} must be integer American odds")
    result = int(value)
    if -100 < result < 100:
        raise OperationalTotalsError(f"{field} must be <= -100 or >= +100")
    return result


def parse_totals_payload(
    payload: object,
    *,
    home_name: str,
    away_name: str,
    collected_at: datetime,
) -> tuple[dict[str, Any], ...]:
    """Extract one unambiguous totals market per required book from one response."""
    if not isinstance(payload, list):
        raise OperationalTotalsError("provider payload must be an array")
    matches = [
        event for event in payload if isinstance(event, dict)
        and event.get("home_team") == home_name and event.get("away_team") == away_name
    ]
    if len(matches) != 1:
        raise OperationalTotalsError("provider game match must be unique")
    raw_books = matches[0].get("bookmakers")
    if not isinstance(raw_books, list):
        raise OperationalTotalsError("provider game has no bookmakers")
    if collected_at.tzinfo is None:
        raise OperationalTotalsError("collected_at must include a timezone")
    collected = collected_at.astimezone(UTC)
    parsed: dict[str, dict[str, Any]] = {}
    for raw_book in raw_books:
        if not isinstance(raw_book, dict) or raw_book.get("key") not in BOOKS:
            continue
        key = raw_book["key"]
        if key in parsed:
            raise OperationalTotalsError(f"duplicate bookmaker: {key}")
        observed_text = raw_book.get("last_update")
        observed = parse_timestamp(observed_text, f"{key}.last_update")
        age = (collected - observed).total_seconds() / 60.0
        if age < 0:
            raise OperationalTotalsError(f"{key} timestamp is after collection")
        if age > MAX_QUOTE_AGE_MINUTES:
            raise OperationalTotalsError(f"{key} totals price is stale")
        markets = raw_book.get("markets")
        totals = [m for m in markets or [] if isinstance(m, dict) and m.get("key") == "totals"]
        if len(totals) != 1:
            raise OperationalTotalsError(f"{key} totals market must be unique")
        outcomes = totals[0].get("outcomes")
        if not isinstance(outcomes, list):
            raise OperationalTotalsError(f"{key} totals outcomes are missing")
        by_name = {item.get("name"): item for item in outcomes if isinstance(item, dict)}
        if set(by_name) != {"Over", "Under"} or len(outcomes) != 2:
            raise OperationalTotalsError(f"{key} requires exactly Over and Under")
        over, under = by_name["Over"], by_name["Under"]
        over_point = _number(over.get("point"), f"{key}.Over.point")
        under_point = _number(under.get("point"), f"{key}.Under.point")
        if over_point != under_point or not 0.0 < over_point < 200.0:
            raise OperationalTotalsError(f"{key} totals points are invalid or mismatched")
        parsed[key] = {
            "bookmaker_key": key,
            "bookmaker": BOOKS[key],
            "total": over_point,
            "over_price": _price(over.get("price"), f"{key}.Over.price"),
            "under_price": _price(under.get("price"), f"{key}.Under.price"),
            "observed_at": observed_text,
        }
    if set(parsed) != set(BOOKS):
        raise OperationalTotalsError("all three required totals books are required")
    return tuple(parsed[key] for key in BOOKS)


def _validate_record(record: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "record_type", "classification", "prospective_evidence",
        "game", "timing", "provider", "books",
    }
    if set(record) != required and set(record) != required | {"observation_id"}:
        raise OperationalTotalsError("totals fields do not match immutable schema")
    if record.get("schema_version") != SCHEMA_VERSION or record.get("record_type") != RECORD_TYPE:
        raise OperationalTotalsError("unsupported totals schema")
    if record.get("classification") != CLASSIFICATION or record.get("prospective_evidence") is not False:
        raise OperationalTotalsError("invalid totals classification")
    game = record.get("game")
    timing = record.get("timing")
    if not isinstance(game, Mapping) or not isinstance(timing, Mapping):
        raise OperationalTotalsError("game and timing must be objects")
    game_fields = {"game_id", "season", "week", "season_type", "home_team", "away_team", "kickoff_at"}
    timing_fields = {"collected_at", "minutes_before_kickoff", "target_label", "target_minutes", "target_deviation_minutes"}
    if set(game) != game_fields or set(timing) != timing_fields:
        raise OperationalTotalsError("game or timing fields are invalid")
    if (
        not isinstance(game["game_id"], str)
        or not game["game_id"]
        or game["season"] != 2026
        or isinstance(game["week"], bool)
        or not isinstance(game["week"], int)
        or not 1 <= game["week"] <= 18
        or game["season_type"] != "REG"
        or not isinstance(game["home_team"], str)
        or not isinstance(game["away_team"], str)
        or not game["home_team"]
        or not game["away_team"]
        or game["home_team"] == game["away_team"]
    ):
        raise OperationalTotalsError("invalid canonical 2026 game identity")
    kickoff = parse_timestamp(game["kickoff_at"], "kickoff_at")
    collected = parse_timestamp(timing["collected_at"], "collected_at")
    actual = _number(timing["minutes_before_kickoff"], "minutes_before_kickoff")
    if actual <= 0 or not math.isclose(actual, (kickoff - collected).total_seconds() / 60, abs_tol=1e-12):
        raise OperationalTotalsError("totals observation must be strictly pre-kickoff")
    target = timing["target_label"]
    provider = record.get("provider")
    if target == "MANUAL":
        if provider != MANUAL_PROVIDER or timing["target_minutes"] is not None or timing["target_deviation_minutes"] is not None:
            raise OperationalTotalsError("invalid manual totals provenance")
    else:
        if target not in TARGET_WINDOWS or provider != AUTOMATIC_PROVIDER_PREFIX + str(target):
            raise OperationalTotalsError("invalid automatic totals provider marker")
        target_minutes, low, high = TARGET_WINDOWS[target]
        if timing["target_minutes"] != target_minutes or not low <= actual <= high:
            raise OperationalTotalsError("automatic totals timing is outside target window")
        deviation = _number(timing["target_deviation_minutes"], "target deviation")
        if not math.isclose(deviation, actual - target_minutes, abs_tol=1e-12):
            raise OperationalTotalsError("target deviation is inconsistent")
    books = record.get("books")
    if not isinstance(books, list) or len(books) != 3:
        raise OperationalTotalsError("exactly three totals books are required")
    keys: set[str] = set()
    for book in books:
        if not isinstance(book, Mapping) or set(book) != {"bookmaker_key", "bookmaker", "total", "over_price", "under_price", "observed_at"}:
            raise OperationalTotalsError("invalid totals book schema")
        key = book["bookmaker_key"]
        if key not in BOOKS or book["bookmaker"] != BOOKS[key] or key in keys:
            raise OperationalTotalsError("invalid or duplicate totals bookmaker")
        keys.add(key)
        point = _number(book["total"], f"{key}.total")
        if not 0 < point < 200:
            raise OperationalTotalsError("totals point is unreasonable")
        _price(book["over_price"], f"{key}.over_price")
        _price(book["under_price"], f"{key}.under_price")
        observed = parse_timestamp(book["observed_at"], f"{key}.observed_at")
        age = (collected - observed).total_seconds() / 60
        if not 0 <= age <= MAX_QUOTE_AGE_MINUTES:
            raise OperationalTotalsError("totals observed timestamp is invalid")


def build_totals_observation(
    game: Mapping[str, Any], books: Sequence[Mapping[str, Any]], *, collected_at: datetime,
    target_label: str, provider: str,
) -> dict[str, Any]:
    kickoff = parse_timestamp(game["kickoff_at"], "kickoff_at")
    if collected_at.tzinfo is None:
        raise OperationalTotalsError("collected_at must include a timezone")
    collected = collected_at.astimezone(UTC)
    actual = (kickoff - collected).total_seconds() / 60
    target_minutes = None if target_label == "MANUAL" else TARGET_WINDOWS[target_label][0]
    base = {
        "schema_version": 1, "record_type": RECORD_TYPE, "classification": CLASSIFICATION,
        "prospective_evidence": False,
        "game": {
            **{
                field: game[field]
                for field in ("game_id", "season", "week", "season_type", "home_team", "away_team")
            },
            "kickoff_at": kickoff.isoformat().replace("+00:00", "Z"),
        },
        "timing": {"collected_at": collected.isoformat().replace("+00:00", "Z"), "minutes_before_kickoff": actual,
                   "target_label": target_label, "target_minutes": target_minutes,
                   "target_deviation_minutes": None if target_minutes is None else actual - target_minutes},
        "provider": provider, "books": [dict(book) for book in books],
    }
    _validate_record(base)
    return {**base, "observation_id": hashlib.sha256(canonical_json(base).encode()).hexdigest()}


def read_totals_history(path: Path | str) -> tuple[dict[str, Any], ...]:
    history_path = Path(path)
    if not history_path.exists():
        return ()
    rows, automatic = [], set()
    for number, line in enumerate(history_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise OperationalTotalsError(f"invalid totals JSON at line {number}") from exc
        material = dict(row) if isinstance(row, dict) else {}
        identity = material.pop("observation_id", None)
        if identity != hashlib.sha256(canonical_json(material).encode()).hexdigest():
            raise OperationalTotalsError(f"invalid totals identity at line {number}")
        _validate_record(row)
        if row["timing"]["target_label"] != "MANUAL":
            key = (row["game"]["game_id"], row["timing"]["target_label"])
            if key in automatic:
                raise OperationalTotalsError("duplicate automatic totals target")
            automatic.add(key)
        rows.append(row)
    return tuple(rows)


def append_totals_observation(path: Path | str, record: Mapping[str, Any]) -> None:
    _validate_record(record)
    material = dict(record)
    identity = material.pop("observation_id", None)
    if identity != hashlib.sha256(canonical_json(material).encode()).hexdigest():
        raise OperationalTotalsError("invalid totals observation identity")
    existing = read_totals_history(path)
    key = (record["game"]["game_id"], record["timing"]["target_label"])
    if record["timing"]["target_label"] != "MANUAL" and any(
        (row["game"]["game_id"], row["timing"]["target_label"]) == key for row in existing
    ):
        raise DuplicateTotalsObservationError("automatic totals target already exists")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
