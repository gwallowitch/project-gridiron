"""Offline Step 92E parser and quality audit for saved historical snapshots."""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from statistics import median
from typing import Any

from gridiron.market.historical_spread_manifest import BOOKMAKER_KEYS, PROVIDER
from gridiron.market.operational_history import canonical_json
from gridiron.market.operational_spreads import BOOKS, parse_timestamp

PARSER_VERSION = "step92e-v1"
READINESS_STATES = {
    "HISTORICAL_SAMPLE_NOT_ACQUIRED", "HISTORICAL_SAMPLE_AUDIT_FAILED",
    "HISTORICAL_SAMPLE_AUDIT_PARTIAL", "HISTORICAL_SAMPLE_AUDIT_PASSED",
}


class HistoricalSpreadError(ValueError):
    """Saved historical evidence cannot be audited safely."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_raw_artifact_metadata(
    raw_bytes: bytes,
    manifest_item: Mapping[str, Any],
    *,
    manifest_sha256: str,
    acquired_at: datetime,
    http_status: int,
    returned_snapshot_timestamp: str,
) -> dict[str, Any]:
    """Describe retained bytes without URLs, headers, credentials, or secrets."""
    if acquired_at.tzinfo is None:
        raise HistoricalSpreadError("acquired_at must include a timezone")
    parse_timestamp(returned_snapshot_timestamp, "returned_snapshot_timestamp")
    return {
        "schema_version": 1,
        "provider": PROVIDER,
        "manifest_item_id": manifest_item["manifest_item_id"],
        "manifest_sha256": manifest_sha256,
        "requested_historical_timestamp": manifest_item["target_timestamp"],
        "returned_snapshot_timestamp": returned_snapshot_timestamp,
        "acquired_at": acquired_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "http_status": http_status,
        "raw_artifact_sha256": _sha(raw_bytes),
        "raw_byte_count": len(raw_bytes),
    }


def _price(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HistoricalSpreadError("INVALID_PRICE")
    if not math.isfinite(float(value)) or int(value) != value:
        raise HistoricalSpreadError("INVALID_PRICE")
    result = int(value)
    if -100 < result < 100:
        raise HistoricalSpreadError("INVALID_PRICE")
    return result


def _point(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HistoricalSpreadError("INVALID_POINT")
    result = float(value)
    if not math.isfinite(result):
        raise HistoricalSpreadError("INVALID_POINT")
    return 0.0 if result == 0 else result


def parse_saved_historical_snapshot(
    payload: object,
    raw_bytes: bytes,
    metadata: Mapping[str, Any],
    manifest_item: Mapping[str, Any],
    *,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    """Audit one saved response. No network, outcomes, or operational freshness."""
    if metadata.get("raw_artifact_sha256") != _sha(raw_bytes):
        raise HistoricalSpreadError("RAW_SHA_MISMATCH")
    if metadata.get("manifest_sha256") != expected_manifest_sha256:
        raise HistoricalSpreadError("MANIFEST_SHA_MISMATCH")
    if metadata.get("manifest_item_id") != manifest_item.get("manifest_item_id"):
        raise HistoricalSpreadError("MANIFEST_ITEM_MISMATCH")
    if metadata.get("provider") != PROVIDER:
        raise HistoricalSpreadError("PROVIDER_MISMATCH")
    material = dict(manifest_item)
    claimed_item_id = material.pop("manifest_item_id", None)
    if claimed_item_id != _sha(canonical_json(material).encode()):
        raise HistoricalSpreadError("MANIFEST_ITEM_MISMATCH")
    if metadata.get("requested_historical_timestamp") != manifest_item.get(
        "target_timestamp"
    ):
        raise HistoricalSpreadError("REQUEST_TIMESTAMP_MISMATCH")
    if metadata.get("http_status") != 200:
        raise HistoricalSpreadError("HTTP_STATUS_INVALID")
    if not isinstance(payload, Mapping) or not {"timestamp", "data"} <= set(payload):
        raise HistoricalSpreadError("MALFORMED_PAYLOAD")
    target = parse_timestamp(manifest_item["target_timestamp"], "target_timestamp")
    snapshot = parse_timestamp(payload["timestamp"], "snapshot_timestamp")
    if snapshot > target:
        raise HistoricalSpreadError("SNAPSHOT_AFTER_TARGET")
    if metadata.get("returned_snapshot_timestamp") != payload["timestamp"]:
        raise HistoricalSpreadError("SNAPSHOT_METADATA_MISMATCH")
    data = payload["data"]
    if not isinstance(data, list):
        raise HistoricalSpreadError("MALFORMED_PAYLOAD")
    matches = [
        event for event in data
        if isinstance(event, Mapping)
        and event.get("home_team") == manifest_item["home_team"]
        and event.get("away_team") == manifest_item["away_team"]
        and event.get("commence_time") == manifest_item["kickoff_at"]
    ]
    if len(matches) != 1:
        raise HistoricalSpreadError("EVENT_IDENTITY_MISMATCH")
    event = matches[0]
    event_id = event.get("id")
    if not isinstance(event_id, str) or not event_id:
        raise HistoricalSpreadError("EVENT_IDENTITY_MISMATCH")
    kickoff = parse_timestamp(manifest_item["kickoff_at"], "kickoff_at")
    raw_books = event.get("bookmakers")
    if not isinstance(raw_books, list):
        raise HistoricalSpreadError("MALFORMED_PAYLOAD")
    by_key: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for book in raw_books:
        if isinstance(book, Mapping) and book.get("key") in BOOKMAKER_KEYS:
            by_key[str(book["key"])].append(book)
    books: list[dict[str, Any]] = []
    for key in BOOKMAKER_KEYS:
        base = {
            "bookmaker_key": key, "canonical_bookmaker": BOOKS[key],
            "book_present": bool(by_key[key]), "market_present": False,
            "accepted": False, "rejection_reason": None,
        }
        try:
            if len(by_key[key]) != 1:
                raise HistoricalSpreadError("MISSING_BOOK" if not by_key[key] else "AMBIGUOUS_BOOK")
            book = by_key[key][0]
            markets = book.get("markets")
            if not isinstance(markets, list):
                raise HistoricalSpreadError("MISSING_MARKET")
            spreads = [
                market for market in markets
                if isinstance(market, Mapping) and market.get("key") == "spreads"
            ]
            if len(spreads) != 1:
                raise HistoricalSpreadError("MISSING_MARKET" if not spreads else "AMBIGUOUS_MAIN_LINE")
            base["market_present"] = True
            market = spreads[0]
            outcomes = market.get("outcomes")
            if not isinstance(outcomes, list) or len(outcomes) != 2:
                raise HistoricalSpreadError("AMBIGUOUS_MAIN_LINE")
            named = {item.get("name"): item for item in outcomes if isinstance(item, Mapping)}
            if set(named) != {manifest_item["home_team"], manifest_item["away_team"]}:
                raise HistoricalSpreadError("OUTCOME_IDENTITY_MISMATCH")
            home = named[manifest_item["home_team"]]
            away = named[manifest_item["away_team"]]
            home_point, away_point = _point(home.get("point")), _point(away.get("point"))
            for raw_point in (home.get("point"), away.get("point")):
                if (
                    isinstance(raw_point, (int, float))
                    and not isinstance(raw_point, bool)
                    and float(raw_point) == 0.0
                    and math.copysign(1.0, float(raw_point)) < 0
                ):
                    raise HistoricalSpreadError("NEGATIVE_ZERO_NOT_CANONICAL")
            if away_point != -home_point:
                raise HistoricalSpreadError("NON_OPPOSING_POINTS")
            updated_text = market.get("last_update", book.get("last_update"))
            updated = parse_timestamp(updated_text, "bookmaker_last_update")
            if updated >= kickoff:
                raise HistoricalSpreadError("QUOTE_AT_OR_AFTER_KICKOFF")
            if updated > target:
                raise HistoricalSpreadError("QUOTE_AFTER_TARGET")
            if updated > snapshot:
                raise HistoricalSpreadError("QUOTE_AFTER_SNAPSHOT")
            base.update(
                {
                    "market_key": "spreads", "bookmaker_last_update": updated_text,
                    "home_team": manifest_item["home_team"], "home_points": home_point,
                    "home_price": _price(home.get("price")),
                    "away_team": manifest_item["away_team"], "away_points": away_point,
                    "away_price": _price(away.get("price")),
                    "provider_returned_odds_format": manifest_item["odds_format"],
                    "conversion_method": None,
                    "quote_age_at_target_seconds": (target - updated).total_seconds(),
                    "accepted": True,
                }
            )
        except (HistoricalSpreadError, ValueError) as exc:
            base["rejection_reason"] = str(exc)
        books.append(base)
    result = {
        "schema_version": 1,
        "classification": "NON_PROSPECTIVE_HISTORICAL_SPREAD_QUALITY_RECORD",
        "prospective_evidence": False,
        "provider": PROVIDER,
        "parser_version": PARSER_VERSION,
        "manifest_item_id": manifest_item["manifest_item_id"],
        "manifest_sha256": expected_manifest_sha256,
        "raw_artifact_sha256": metadata["raw_artifact_sha256"],
        "canonical_game_id": manifest_item["canonical_game_id"],
        "provider_event_id": event_id,
        "season": manifest_item["season"],
        "season_type": manifest_item["season_type"],
        "week": manifest_item["week"],
        "home_team": manifest_item["home_team"],
        "away_team": manifest_item["away_team"],
        "kickoff_at": manifest_item["kickoff_at"],
        "target_label": manifest_item["target_label"],
        "requested_target_timestamp": manifest_item["target_timestamp"],
        "provider_snapshot_timestamp": payload["timestamp"],
        "target_lag_seconds": (target - snapshot).total_seconds(),
        "books": books,
    }
    return {**result, "quality_record_id": _sha(canonical_json(result).encode())}


def _percentile90(values: Sequence[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.9 * len(ordered)) - 1)]


def audit_historical_records(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate market quality only; deliberately has no outcome calculations."""
    if not records:
        return {
            "readiness": "HISTORICAL_SAMPLE_NOT_ACQUIRED", "records": 0,
            "accepted_books": 0, "rejection_reasons": {}, "lag_statistics": [],
        }
    reasons: Counter[str] = Counter()
    accepted = 0
    groups: dict[tuple[int, str, str], list[float]] = defaultdict(list)
    all_three = two = one = none = 0
    for record in records:
        count = 0
        for book in record["books"]:
            if book["accepted"]:
                accepted += 1
                count += 1
                groups[(record["season"], record["target_label"], book["bookmaker_key"])].append(
                    book["quote_age_at_target_seconds"]
                )
            else:
                reasons[str(book["rejection_reason"])] += 1
        all_three += count == 3
        two += count == 2
        one += count == 1
        none += count == 0
    stats = [
        {
            "season": season, "target_label": target, "bookmaker_key": book,
            "minimum": min(values), "median": median(values),
            "p90": _percentile90(values), "maximum": max(values),
        }
        for (season, target, book), values in sorted(groups.items())
    ]
    readiness = (
        "HISTORICAL_SAMPLE_AUDIT_FAILED" if accepted == 0
        else "HISTORICAL_SAMPLE_AUDIT_PARTIAL"
    )
    return {
        "readiness": readiness, "records": len(records), "accepted_books": accepted,
        "all_three_books_complete": all_three, "two_books_complete": two,
        "one_book_complete": one, "no_book": none,
        "rejection_reasons": dict(sorted(reasons.items())), "lag_statistics": stats,
    }


__all__ = [
    "READINESS_STATES",
    "HistoricalSpreadError",
    "audit_historical_records",
    "build_raw_artifact_metadata",
    "parse_saved_historical_snapshot",
]
