"""Pure append-only lifecycle events for inactive Core-Three rehearsals."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from gridiron.market.core_three_provider import parse_timestamp
from gridiron.market.core_three_types import (
    EVIDENCE_ID,
    PROTOCOL_ID,
    CoreThreeError,
    validate_identity,
    validate_safe_strings,
)

EVENT_TYPES = {
    "SCHEDULED",
    "CAPTURE_ACCEPTED",
    "CAPTURE_REJECTED",
    "GAME_POSTPONED",
    "SCHEDULE_REVISION",
    "DECISION_VOID_SCHEDULE_CHANGE",
    "GAME_CANCELLED",
}


def append_event(
    events: Sequence[Mapping[str, Any]], payload: Mapping[str, Any]
) -> tuple[dict[str, Any], ...]:
    """Return a new validated hash chain; never mutate the supplied events."""
    prior = tuple(deepcopy(dict(event)) for event in events)
    payload = deepcopy(dict(payload))
    validate_safe_strings(payload)
    validate_identity(payload)
    if any(key in payload for key in ("sequence", "previous_hash", "event_hash")):
        raise CoreThreeError("LIFECYCLE_RESERVED_METADATA")
    validate_chain(prior)
    event_type = payload.get("event_type")
    if not isinstance(event_type, str) or event_type not in EVENT_TYPES:
        raise CoreThreeError("UNKNOWN_LIFECYCLE_EVENT")
    game_id = payload.get("game_id")
    if not isinstance(game_id, str) or not game_id:
        raise CoreThreeError("LIFECYCLE_GAME_ID_REQUIRED")
    _validate_transition(prior, event_type, game_id, payload)
    event = {
        "protocol_id": PROTOCOL_ID,
        "evidence_id": EVIDENCE_ID,
        "sequence": len(prior) + 1,
        "previous_hash": prior[-1]["event_hash"] if prior else None,
        **dict(payload),
        "prospective_evidence": False,
    }
    event["event_hash"] = _hash({k: v for k, v in event.items() if k != "event_hash"})
    result = (*prior, event)
    validate_chain(result)
    return result


def validate_chain(events: Sequence[Mapping[str, Any]]) -> None:
    previous = None
    for index, event in enumerate(events, start=1):
        validate_identity(dict(event))
        if (
            event.get("protocol_id") != PROTOCOL_ID
            or event.get("evidence_id") != EVIDENCE_ID
        ):
            raise CoreThreeError("CORE_THREE_IDENTITY_MISMATCH")
        if event.get("prospective_evidence") is not False:
            raise CoreThreeError("CORE_THREE_IDENTITY_MISMATCH")
        if event.get("sequence") != index or event.get("previous_hash") != previous:
            raise CoreThreeError("LIFECYCLE_CHAIN_BROKEN")
        expected = _hash({k: v for k, v in event.items() if k != "event_hash"})
        if event.get("event_hash") != expected:
            raise CoreThreeError("LIFECYCLE_HASH_MISMATCH")
        validate_safe_strings(dict(event))
        event_type = event.get("event_type")
        game_id = event.get("game_id")
        if not isinstance(event_type, str) or event_type not in EVENT_TYPES:
            raise CoreThreeError("UNKNOWN_LIFECYCLE_EVENT")
        if not isinstance(game_id, str) or not game_id:
            raise CoreThreeError("LIFECYCLE_GAME_ID_REQUIRED")
        _validate_transition(tuple(events[: index - 1]), event_type, game_id, event)
        previous = expected


def _validate_transition(
    events: tuple[dict[str, Any], ...],
    event_type: str,
    game_id: str,
    payload: Mapping[str, Any],
) -> None:
    same = [event for event in events if event.get("game_id") == game_id]
    accepted = any(event.get("event_type") == "CAPTURE_ACCEPTED" for event in same)
    cancelled = any(event.get("event_type") == "GAME_CANCELLED" for event in same)
    if cancelled:
        raise CoreThreeError("CANCELLED_GAME_IS_TERMINAL")
    if event_type == "SCHEDULED":
        if same:
            raise CoreThreeError("DUPLICATE_SCHEDULE")
        if "kickoff_at" in payload:
            parse_timestamp(payload["kickoff_at"], "kickoff_at")
        return
    if not same or same[0]["event_type"] != "SCHEDULED":
        raise CoreThreeError("PRECEDING_SCHEDULE_REQUIRED")
    voided = any(
        event["event_type"] == "DECISION_VOID_SCHEDULE_CHANGE" for event in same
    )
    if event_type == "CAPTURE_ACCEPTED" and accepted:
        raise CoreThreeError("ACCEPTED_CAPTURE_IMMUTABLE")
    if voided:
        raise CoreThreeError("VOIDED_DECISION_TERMINAL")
    schedule_events = [
        event
        for event in same
        if event["event_type"] in {"SCHEDULED", "SCHEDULE_REVISION", "GAME_POSTPONED"}
    ]
    postponed = schedule_events[-1]["event_type"] == "GAME_POSTPONED"
    if event_type == "CAPTURE_ACCEPTED" and postponed:
        raise CoreThreeError("POSTPONED_GAME_REQUIRES_VALID_REVISION")
    if event_type == "GAME_POSTPONED" and (postponed or accepted):
        raise CoreThreeError("INVALID_POSTPONEMENT_REQUIRES_VOID_IF_ACCEPTED")
    if event_type == "SCHEDULE_REVISION":
        required = {"old_kickoff_at", "new_kickoff_at", "detected_at"}
        if not required.issubset(payload):
            raise CoreThreeError("SCHEDULE_REVISION_FIELDS_REQUIRED")
        if accepted:
            raise CoreThreeError("ACCEPTED_GAME_REQUIRES_VOID_NOT_REVISION")
        old = parse_timestamp(payload["old_kickoff_at"], "old_kickoff_at")
        new = parse_timestamp(payload["new_kickoff_at"], "new_kickoff_at")
        detected = parse_timestamp(payload["detected_at"], "detected_at")
        if old == new or detected >= new:
            raise CoreThreeError("INVALID_SCHEDULE_REVISION")
        schedules = [
            event
            for event in same
            if event["event_type"] in {"SCHEDULED", "SCHEDULE_REVISION"}
        ]
        current = schedules[-1].get("new_kickoff_at", schedules[-1].get("kickoff_at"))
        if current is not None and parse_timestamp(current, "current_kickoff") != old:
            raise CoreThreeError("REVISION_OLD_KICKOFF_MISMATCH")
        prior_detection = schedules[-1].get("detected_at")
        if prior_detection is not None and detected < parse_timestamp(
            prior_detection, "detected_at"
        ):
            raise CoreThreeError("REVISION_DETECTION_OUT_OF_ORDER")
    if event_type == "DECISION_VOID_SCHEDULE_CHANGE" and not accepted:
        raise CoreThreeError("VOID_REQUIRES_ACCEPTED_CAPTURE")
    if accepted and event_type == "CAPTURE_ACCEPTED":
        raise CoreThreeError("ACCEPTED_CAPTURE_IMMUTABLE")


def _hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
