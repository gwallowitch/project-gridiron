"""Pure append-only lifecycle events for inactive Core-Three rehearsals."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from gridiron.market.core_three_types import CoreThreeError, PROTOCOL_ID

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
    prior = tuple(dict(event) for event in events)
    validate_chain(prior)
    event_type = payload.get("event_type")
    if event_type not in EVENT_TYPES:
        raise CoreThreeError("UNKNOWN_LIFECYCLE_EVENT")
    game_id = payload.get("game_id")
    if not isinstance(game_id, str) or not game_id:
        raise CoreThreeError("LIFECYCLE_GAME_ID_REQUIRED")
    _validate_transition(prior, event_type, game_id, payload)
    event = {
        "protocol_id": PROTOCOL_ID,
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
        if event.get("sequence") != index or event.get("previous_hash") != previous:
            raise CoreThreeError("LIFECYCLE_CHAIN_BROKEN")
        expected = _hash({k: v for k, v in event.items() if k != "event_hash"})
        if event.get("event_hash") != expected:
            raise CoreThreeError("LIFECYCLE_HASH_MISMATCH")
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
    if event_type == "SCHEDULE_REVISION":
        required = {"old_kickoff_at", "new_kickoff_at", "detected_at"}
        if not required.issubset(payload):
            raise CoreThreeError("SCHEDULE_REVISION_FIELDS_REQUIRED")
        if accepted:
            raise CoreThreeError("ACCEPTED_GAME_REQUIRES_VOID_NOT_REVISION")
    if event_type == "DECISION_VOID_SCHEDULE_CHANGE" and not accepted:
        raise CoreThreeError("VOID_REQUIRES_ACCEPTED_CAPTURE")
    if accepted and event_type == "CAPTURE_ACCEPTED":
        raise CoreThreeError("ACCEPTED_CAPTURE_IMMUTABLE")


def _hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
