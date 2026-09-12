"""Append-only non-prospective Step 91Q collection-attempt metadata."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gridiron.market.operational_history import canonical_json

SCHEMA_VERSION = 1
RECORD_TYPE = "OPERATIONAL_MARKET_COLLECTION_ATTEMPT"
CLASSIFICATION = "NON_PROSPECTIVE_OPERATIONAL_COLLECTION_ATTEMPT"
RESULTS = {
    "SUCCESS",
    "FAILED",
    "SKIPPED_OUTSIDE_WINDOW",
    "DUPLICATE_TARGET",
    "POST_KICKOFF",
}
REASON_CODES = {
    "SUCCESS",
    "RECOVERED_SUCCESS",
    "ALREADY_COMPLETE",
    "OUTSIDE_WINDOW",
    "MISSED_WINDOW",
    "POST_KICKOFF",
    "ODDS_PROVIDER_ERROR",
    "MISSING_BOOK",
    "STALE_PRICE",
    "INVALID_TIMESTAMP",
    "DEF_EPA_UNAVAILABLE",
    "OPERATIONAL_VALIDATION_FAILED",
    "HISTORY_APPEND_FAILED",
    "ATTEMPT_LOG_APPEND_FAILED",
}
TARGET_MINUTES = {
    "T12H": 720,
    "T6H": 360,
    "T3H": 180,
    "T1H": 60,
    "NEAR_KICKOFF": 15,
}
BASE_FIELDS = {
    "schema_version",
    "record_type",
    "classification",
    "game_id",
    "collection_target",
    "target_minutes_to_kickoff",
    "target_time",
    "attempted_at",
    "kickoff_at",
    "actual_minutes_to_kickoff",
    "target_deviation_minutes",
    "result",
    "reason_code",
    "observation_id",
}


class CollectionAttemptError(ValueError):
    """Collection-attempt history is malformed or contradictory."""


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise CollectionAttemptError(f"{field} must be an ISO-8601 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise CollectionAttemptError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise CollectionAttemptError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CollectionAttemptError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CollectionAttemptError(f"{field} must be finite")
    return result


def validate_collection_attempt(record: Mapping[str, Any]) -> None:
    """Validate one attempt independently of its content hash."""
    allowed = (BASE_FIELDS, BASE_FIELDS | {"attempt_id"})
    if not any(set(record) == fields for fields in allowed):
        raise CollectionAttemptError("attempt fields do not match the immutable schema")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise CollectionAttemptError("unsupported attempt schema_version")
    if record.get("record_type") != RECORD_TYPE:
        raise CollectionAttemptError("invalid attempt record_type")
    if record.get("classification") != CLASSIFICATION:
        raise CollectionAttemptError("invalid attempt classification")
    game_id = record.get("game_id")
    target = record.get("collection_target")
    if not isinstance(game_id, str) or not game_id:
        raise CollectionAttemptError("invalid attempt game_id")
    if not isinstance(target, str) or target not in TARGET_MINUTES:
        raise CollectionAttemptError("invalid collection_target")
    target_minutes = record.get("target_minutes_to_kickoff")
    if (
        isinstance(target_minutes, bool)
        or not isinstance(target_minutes, int)
        or target_minutes != TARGET_MINUTES[target]
    ):
        raise CollectionAttemptError("target minutes do not match collection_target")
    target_time = _timestamp(record.get("target_time"), "target_time")
    attempted = _timestamp(record.get("attempted_at"), "attempted_at")
    kickoff = _timestamp(record.get("kickoff_at"), "kickoff_at")
    actual = _number(record.get("actual_minutes_to_kickoff"), "actual minutes")
    deviation = _number(record.get("target_deviation_minutes"), "target deviation")
    expected_target = kickoff.timestamp() - target_minutes * 60.0
    if not math.isclose(target_time.timestamp(), expected_target, abs_tol=1e-6):
        raise CollectionAttemptError("target_time is inconsistent")
    expected_actual = (kickoff - attempted).total_seconds() / 60.0
    if not math.isclose(actual, expected_actual, abs_tol=1e-12):
        raise CollectionAttemptError("actual_minutes_to_kickoff is inconsistent")
    if not math.isclose(deviation, actual - target_minutes, abs_tol=1e-12):
        raise CollectionAttemptError("target_deviation_minutes is inconsistent")
    result = record.get("result")
    reason = record.get("reason_code")
    if result not in RESULTS or reason not in REASON_CODES:
        raise CollectionAttemptError("invalid attempt result or reason_code")
    observation_id = record.get("observation_id")
    expected_reasons = {
        "FAILED": {
            "ODDS_PROVIDER_ERROR",
            "MISSING_BOOK",
            "STALE_PRICE",
            "INVALID_TIMESTAMP",
            "DEF_EPA_UNAVAILABLE",
            "OPERATIONAL_VALIDATION_FAILED",
            "HISTORY_APPEND_FAILED",
        },
        "SKIPPED_OUTSIDE_WINDOW": {"OUTSIDE_WINDOW", "MISSED_WINDOW"},
        "DUPLICATE_TARGET": {"ALREADY_COMPLETE"},
        "POST_KICKOFF": {"POST_KICKOFF"},
    }
    if result == "SUCCESS":
        if reason not in {"SUCCESS", "RECOVERED_SUCCESS"} or not isinstance(observation_id, str) or not observation_id:
            raise CollectionAttemptError("successful attempt requires observation identity")
    else:
        if reason not in expected_reasons[result]:
            raise CollectionAttemptError("attempt result and reason_code are inconsistent")
        if observation_id is not None:
            raise CollectionAttemptError("unsuccessful attempt cannot link an observation")


def build_collection_attempt(
    *,
    game_id: str,
    collection_target: str,
    target_minutes_to_kickoff: int,
    kickoff_at: str,
    attempted_at: datetime,
    result: str,
    reason_code: str,
    observation_id: str | None = None,
) -> dict[str, Any]:
    """Build one canonical collection-attempt record."""
    kickoff = _timestamp(kickoff_at, "kickoff_at")
    if attempted_at.tzinfo is None:
        raise CollectionAttemptError("attempted_at must include a timezone")
    attempted = attempted_at.astimezone(UTC)
    actual = (kickoff - attempted).total_seconds() / 60.0
    target_time = datetime.fromtimestamp(
        kickoff.timestamp() - target_minutes_to_kickoff * 60.0, UTC
    )
    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "classification": CLASSIFICATION,
        "game_id": game_id,
        "collection_target": collection_target,
        "target_minutes_to_kickoff": target_minutes_to_kickoff,
        "target_time": target_time.isoformat().replace("+00:00", "Z"),
        "attempted_at": attempted.isoformat().replace("+00:00", "Z"),
        "kickoff_at": kickoff.isoformat().replace("+00:00", "Z"),
        "actual_minutes_to_kickoff": actual,
        "target_deviation_minutes": actual - target_minutes_to_kickoff,
        "result": result,
        "reason_code": reason_code,
        "observation_id": observation_id,
    }
    validate_collection_attempt(base)
    identity = hashlib.sha256(canonical_json(base).encode("utf-8")).hexdigest()
    return {**base, "attempt_id": identity}


def read_collection_attempts(path: Path | str) -> tuple[dict[str, Any], ...]:
    """Read an entire attempt log and reject corruption or duplicate targets."""
    attempt_path = Path(path)
    if not attempt_path.exists():
        return ()
    records: list[dict[str, Any]] = []
    targets: set[tuple[str, str]] = set()
    identities: set[str] = set()
    for line_number, line in enumerate(
        attempt_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            raise CollectionAttemptError(f"blank attempt line {line_number}")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CollectionAttemptError(f"invalid attempt JSON at line {line_number}") from exc
        if not isinstance(record, dict):
            raise CollectionAttemptError(f"attempt line {line_number} is not an object")
        material = dict(record)
        identity = material.pop("attempt_id", None)
        expected = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
        if identity != expected:
            raise CollectionAttemptError(f"invalid attempt identity at line {line_number}")
        validate_collection_attempt(record)
        key = (record["game_id"], record["collection_target"])
        if key in targets or identity in identities:
            raise CollectionAttemptError(f"duplicate collection target at line {line_number}")
        targets.add(key)
        identities.add(identity)
        records.append(record)
    return tuple(records)


def append_collection_attempt(path: Path | str, record: Mapping[str, Any]) -> None:
    """Append one validated target attempt exactly once."""
    validate_collection_attempt(record)
    material = dict(record)
    identity = material.pop("attempt_id", None)
    expected = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    if identity != expected:
        raise CollectionAttemptError("invalid attempt identity")
    existing = read_collection_attempts(path)
    key = (record["game_id"], record["collection_target"])
    if any((item["game_id"], item["collection_target"]) == key for item in existing):
        raise CollectionAttemptError("collection target already attempted")
    attempt_path = Path(path)
    attempt_path.parent.mkdir(parents=True, exist_ok=True)
    with attempt_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
