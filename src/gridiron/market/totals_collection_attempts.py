"""Immutable Step 91R totals collection-attempt log."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gridiron.market.operational_totals import (
    TARGET_WINDOWS,
    canonical_json,
    parse_timestamp,
)

CLASSIFICATION = "NON_PROSPECTIVE_TOTALS_COLLECTION_ATTEMPT"
RESULTS = {"SUCCESS", "FAILED", "MISSED_WINDOW", "POST_KICKOFF"}
REASONS = {
    "SUCCESS", "RECOVERED_SUCCESS", "MISSED_WINDOW", "POST_KICKOFF",
    "PROVIDER_ERROR", "MISSING_BOOK", "MALFORMED_TOTALS_MARKET", "STALE_PRICE",
    "INVALID_TIMESTAMP", "HISTORY_APPEND_FAILED", "ATTEMPT_LOG_APPEND_FAILED",
    "OPERATIONAL_VALIDATION_FAILED",
}
FIELDS = {
    "schema_version", "classification", "game_id", "target_label", "target_minutes",
    "kickoff_at", "attempted_at", "actual_minutes_before_kickoff", "result",
    "reason_code", "observation_id",
}


class TotalsAttemptError(ValueError):
    """Totals attempt metadata is invalid or corrupt."""


def _validate(record: Mapping[str, Any]) -> None:
    if set(record) != FIELDS and set(record) != FIELDS | {"attempt_id"}:
        raise TotalsAttemptError("totals attempt fields are invalid")
    if record.get("schema_version") != 1 or record.get("classification") != CLASSIFICATION:
        raise TotalsAttemptError("invalid totals attempt identity")
    target = record.get("target_label")
    if not isinstance(target, str) or target not in TARGET_WINDOWS or record.get("target_minutes") != TARGET_WINDOWS[target][0]:
        raise TotalsAttemptError("invalid totals attempt target")
    kickoff = parse_timestamp(record.get("kickoff_at"), "kickoff_at")
    attempted = parse_timestamp(record.get("attempted_at"), "attempted_at")
    actual = record.get("actual_minutes_before_kickoff")
    if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(actual):
        raise TotalsAttemptError("invalid actual totals timing")
    if not math.isclose(float(actual), (kickoff - attempted).total_seconds() / 60, abs_tol=1e-12):
        raise TotalsAttemptError("inconsistent actual totals timing")
    result, reason, linked = record.get("result"), record.get("reason_code"), record.get("observation_id")
    if result not in RESULTS or reason not in REASONS:
        raise TotalsAttemptError("invalid totals attempt result")
    if result == "SUCCESS":
        if reason not in {"SUCCESS", "RECOVERED_SUCCESS"} or not isinstance(linked, str) or not linked:
            raise TotalsAttemptError("successful totals attempt requires linkage")
        _, low, high = TARGET_WINDOWS[target]
        if not low <= float(actual) <= high:
            raise TotalsAttemptError("successful totals attempt is outside target window")
    elif linked is not None:
        raise TotalsAttemptError("unsuccessful totals attempt cannot link observation")
    if result == "MISSED_WINDOW" and reason != "MISSED_WINDOW":
        raise TotalsAttemptError("invalid missed-window reason")
    if result == "POST_KICKOFF" and reason != "POST_KICKOFF":
        raise TotalsAttemptError("invalid post-kickoff reason")
    if result == "FAILED" and reason in {"SUCCESS", "RECOVERED_SUCCESS", "MISSED_WINDOW", "POST_KICKOFF"}:
        raise TotalsAttemptError("invalid failed-attempt reason")


def build_totals_attempt(
    *, game_id: str, target_label: str, kickoff_at: str, attempted_at: datetime,
    result: str, reason_code: str, observation_id: str | None = None,
) -> dict[str, Any]:
    kickoff = parse_timestamp(kickoff_at, "kickoff_at")
    if attempted_at.tzinfo is None:
        raise TotalsAttemptError("attempted_at must include a timezone")
    attempted = attempted_at.astimezone(UTC)
    base = {
        "schema_version": 1, "classification": CLASSIFICATION, "game_id": game_id,
        "target_label": target_label, "target_minutes": TARGET_WINDOWS[target_label][0],
        "kickoff_at": kickoff.isoformat().replace("+00:00", "Z"),
        "attempted_at": attempted.isoformat().replace("+00:00", "Z"),
        "actual_minutes_before_kickoff": (kickoff - attempted).total_seconds() / 60,
        "result": result, "reason_code": reason_code, "observation_id": observation_id,
    }
    _validate(base)
    return {**base, "attempt_id": hashlib.sha256(canonical_json(base).encode()).hexdigest()}


def read_totals_attempts(path: Path | str) -> tuple[dict[str, Any], ...]:
    source = Path(path)
    if not source.exists():
        return ()
    rows, keys = [], set()
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TotalsAttemptError(f"invalid totals attempt JSON at line {number}") from exc
        material = dict(row) if isinstance(row, dict) else {}
        identity = material.pop("attempt_id", None)
        if identity != hashlib.sha256(canonical_json(material).encode()).hexdigest():
            raise TotalsAttemptError(f"invalid totals attempt hash at line {number}")
        _validate(row)
        key = (row["game_id"], row["target_label"])
        if key in keys:
            raise TotalsAttemptError("duplicate totals attempt target")
        keys.add(key)
        rows.append(row)
    return tuple(rows)


def append_totals_attempt(path: Path | str, record: Mapping[str, Any]) -> None:
    _validate(record)
    material = dict(record)
    identity = material.pop("attempt_id", None)
    if identity != hashlib.sha256(canonical_json(material).encode()).hexdigest():
        raise TotalsAttemptError("invalid totals attempt hash")
    existing = read_totals_attempts(path)
    key = (record["game_id"], record["target_label"])
    if any((row["game_id"], row["target_label"]) == key for row in existing):
        raise TotalsAttemptError("totals target already attempted")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
