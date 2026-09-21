"""Immutable non-prospective Step 92B spread collection-attempt contract."""

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
from gridiron.market.operational_spreads import (
    LANE,
    TARGET_WINDOWS,
    ImmutableSpreadConflictError,
    OperationalSpreadError,
    parse_timestamp,
    validate_spread_observation,
)

SCHEMA_VERSION = 1
RECORD_TYPE = "OPERATIONAL_SPREAD_COLLECTION_ATTEMPT"
CLASSIFICATION = "NON_PROSPECTIVE_SPREAD_COLLECTION_ATTEMPT"
RESULTS = {"SUCCESS", "FAILED", "MISSED_WINDOW", "POST_KICKOFF"}
FAILURE_REASONS = {
    "PROVIDER_FAILURE", "MISSING_GAME", "MISSING_BOOK", "MISSING_MARKET",
    "MALFORMED_MARKET", "STALE_QUOTE", "TIMESTAMP_INVALID", "IDENTITY_MISMATCH",
    "CONFLICTING_SPREAD", "HISTORY_APPEND_FAILED", "ATTEMPT_LOG_APPEND_FAILED",
    "OPERATIONAL_VALIDATION_FAILED",
}
REASONS = {"SUCCESS", "RECOVERED_SUCCESS", "MISSED_WINDOW", "POST_KICKOFF"} | FAILURE_REASONS
FIELDS = {
    "schema_version", "record_type", "classification", "lane", "game_id",
    "target_label", "target_minutes", "kickoff_at", "attempted_at",
    "actual_minutes_before_kickoff", "result", "reason_code", "observation_id",
    "raw_response_id",
}


class SpreadAttemptError(OperationalSpreadError):
    """Spread attempt metadata is invalid or corrupt."""


def validate_spread_attempt(record: Mapping[str, Any]) -> None:
    if set(record) not in (FIELDS, FIELDS | {"attempt_id"}):
        raise SpreadAttemptError("spread attempt fields do not match immutable schema")
    if (
        record.get("schema_version") != SCHEMA_VERSION
        or record.get("record_type") != RECORD_TYPE
        or record.get("classification") != CLASSIFICATION
        or record.get("lane") != LANE
    ):
        raise SpreadAttemptError("invalid spread attempt identity")
    if not isinstance(record.get("game_id"), str) or not record["game_id"]:
        raise SpreadAttemptError("invalid spread attempt game_id")
    target = record.get("target_label")
    if target not in TARGET_WINDOWS:
        raise SpreadAttemptError("invalid spread attempt target")
    target_minutes, low, high = TARGET_WINDOWS[str(target)]
    if record.get("target_minutes") != target_minutes:
        raise SpreadAttemptError("spread attempt target minutes are inconsistent")
    kickoff = parse_timestamp(record.get("kickoff_at"), "kickoff_at")
    attempted = parse_timestamp(record.get("attempted_at"), "attempted_at")
    actual = record.get("actual_minutes_before_kickoff")
    if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(float(actual)):
        raise SpreadAttemptError("invalid spread attempt timing")
    if not math.isclose(float(actual), (kickoff - attempted).total_seconds() / 60, abs_tol=1e-12):
        raise SpreadAttemptError("inconsistent spread attempt timing")
    result, reason = record.get("result"), record.get("reason_code")
    observation_id, raw_id = record.get("observation_id"), record.get("raw_response_id")
    if result not in RESULTS or reason not in REASONS:
        raise SpreadAttemptError("invalid spread attempt result or reason")
    if result == "SUCCESS":
        if reason not in {"SUCCESS", "RECOVERED_SUCCESS"}:
            raise SpreadAttemptError("invalid successful spread attempt reason")
        if not isinstance(observation_id, str) or not observation_id:
            raise SpreadAttemptError("successful spread attempt requires observation linkage")
        if not isinstance(raw_id, str) or not raw_id:
            raise SpreadAttemptError("successful spread attempt requires raw linkage")
        if not low <= float(actual) <= high:
            raise SpreadAttemptError("successful spread attempt is outside target window")
    else:
        if observation_id is not None:
            raise SpreadAttemptError("unsuccessful spread attempt cannot link observation")
        if result == "FAILED" and reason not in FAILURE_REASONS:
            raise SpreadAttemptError("invalid failed spread attempt reason")
        if result == "MISSED_WINDOW" and reason != "MISSED_WINDOW":
            raise SpreadAttemptError("invalid missed-window spread attempt reason")
        if result == "POST_KICKOFF" and reason != "POST_KICKOFF":
            raise SpreadAttemptError("invalid post-kickoff spread attempt reason")
    for identity, field in ((observation_id, "observation_id"), (raw_id, "raw_response_id")):
        if identity is not None and (
            not isinstance(identity, str)
            or len(identity) != 64
            or any(char not in "0123456789abcdef" for char in identity)
        ):
            raise SpreadAttemptError(f"invalid {field}")


def build_spread_attempt(
    *,
    game_id: str,
    target_label: str,
    kickoff_at: str,
    attempted_at: datetime,
    result: str,
    reason_code: str,
    observation_id: str | None = None,
    raw_response_id: str | None = None,
) -> dict[str, Any]:
    if target_label not in TARGET_WINDOWS:
        raise SpreadAttemptError("invalid spread attempt target")
    kickoff = parse_timestamp(kickoff_at, "kickoff_at")
    if attempted_at.tzinfo is None:
        raise SpreadAttemptError("attempted_at must include a timezone")
    attempted = attempted_at.astimezone(UTC)
    base = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "game_id": game_id,
        "target_label": target_label,
        "target_minutes": TARGET_WINDOWS[target_label][0],
        "kickoff_at": kickoff.isoformat().replace("+00:00", "Z"),
        "attempted_at": attempted.isoformat().replace("+00:00", "Z"),
        "actual_minutes_before_kickoff": (kickoff - attempted).total_seconds() / 60,
        "result": result,
        "reason_code": reason_code,
        "observation_id": observation_id,
        "raw_response_id": raw_response_id,
    }
    validate_spread_attempt(base)
    return {**base, "attempt_id": hashlib.sha256(canonical_json(base).encode()).hexdigest()}


def validate_spread_success_linkage(
    observation: Mapping[str, Any], attempt: Mapping[str, Any]
) -> None:
    """Bind one successful attempt to its exact canonical observation."""
    validate_spread_observation(observation)
    _validated_identity(attempt)
    if attempt.get("result") != "SUCCESS":
        raise SpreadAttemptError("spread linkage requires a successful attempt")
    material = dict(observation)
    observation_id = material.pop("observation_id", None)
    expected = hashlib.sha256(canonical_json(material).encode()).hexdigest()
    if observation_id != expected:
        raise SpreadAttemptError("linked spread observation identity is invalid")
    if (
        attempt.get("observation_id") != observation_id
        or attempt.get("game_id") != observation["game"]["game_id"]
        or attempt.get("target_label") != observation["timing"]["target_label"]
        or attempt.get("kickoff_at") != observation["game"]["kickoff_at"]
        or attempt.get("raw_response_id") != observation["raw_response_id"]
    ):
        raise SpreadAttemptError("spread attempt and observation linkage is inconsistent")


def _validated_identity(record: Mapping[str, Any]) -> str:
    validate_spread_attempt(record)
    material = dict(record)
    identity = material.pop("attempt_id", None)
    expected = hashlib.sha256(canonical_json(material).encode()).hexdigest()
    if identity != expected:
        raise SpreadAttemptError("invalid spread attempt identity")
    return str(identity)


def read_spread_attempts(path: Path | str) -> tuple[dict[str, Any], ...]:
    source = Path(path)
    if not source.exists():
        return ()
    rows: list[dict[str, Any]] = []
    slots: dict[tuple[str, str], dict[str, Any]] = {}
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SpreadAttemptError(f"invalid spread attempt JSON at line {number}") from exc
        if not isinstance(row, dict):
            raise SpreadAttemptError(f"spread attempt line {number} is not an object")
        _validated_identity(row)
        slot = (row["game_id"], row["target_label"])
        existing = slots.get(slot)
        if existing is not None and existing != row:
            raise ImmutableSpreadConflictError("conflicting immutable spread attempt")
        if existing is None:
            slots[slot] = row
            rows.append(row)
    return tuple(rows)


def append_spread_attempt(path: Path | str, record: Mapping[str, Any]) -> bool:
    """Append a new target attempt; return False for an exact replay."""
    _validated_identity(record)
    slot = (record["game_id"], record["target_label"])
    for existing in read_spread_attempts(path):
        if (existing["game_id"], existing["target_label"]) == slot:
            if existing == dict(record):
                return False
            raise ImmutableSpreadConflictError("conflicting immutable spread attempt")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return True
