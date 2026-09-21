"""Isolated append-only repository coordinator for Step 92C spread evidence."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from gridiron.market.operational_history import canonical_json
from gridiron.market.operational_spreads import (
    OperationalSpreadError,
    append_spread_observation,
    read_spread_history,
    validate_spread_observation,
)
from gridiron.market.spread_collection_attempts import (
    SpreadAttemptError,
    append_spread_attempt,
    read_spread_attempts,
    validate_spread_attempt,
    validate_spread_success_linkage,
)


def _identity(record: Mapping[str, Any], field: str) -> str:
    material = dict(record)
    claimed = material.pop(field, None)
    expected = hashlib.sha256(canonical_json(material).encode()).hexdigest()
    if claimed != expected:
        raise OperationalSpreadError(f"invalid {field}")
    return str(claimed)


def validate_spread_evidence_set(
    observations: Sequence[Mapping[str, Any]],
    attempts: Sequence[Mapping[str, Any]],
) -> None:
    """Validate canonical identities, logical uniqueness, and success links."""
    by_id: dict[str, Mapping[str, Any]] = {}
    observation_slots: dict[tuple[str, str], Mapping[str, Any]] = {}
    for observation in observations:
        validate_spread_observation(observation)
        identity = _identity(observation, "observation_id")
        existing_id = by_id.get(identity)
        if existing_id is not None and existing_id != observation:
            raise OperationalSpreadError("conflicting spread observation identity")
        slot = (
            str(observation["game"]["game_id"]),
            str(observation["timing"]["target_label"]),
        )
        existing_slot = observation_slots.get(slot)
        if existing_slot is not None and existing_slot != observation:
            raise OperationalSpreadError("conflicting spread observation slot")
        by_id[identity] = observation
        observation_slots[slot] = observation
    attempt_slots: dict[tuple[str, str], Mapping[str, Any]] = {}
    for attempt in attempts:
        validate_spread_attempt(attempt)
        _identity(attempt, "attempt_id")
        slot = (str(attempt["game_id"]), str(attempt["target_label"]))
        existing = attempt_slots.get(slot)
        if existing is not None and existing != attempt:
            raise SpreadAttemptError("conflicting spread attempt slot")
        attempt_slots[slot] = attempt
        if attempt["result"] == "SUCCESS":
            linked = by_id.get(str(attempt["observation_id"]))
            if linked is None:
                raise SpreadAttemptError("successful spread attempt references missing observation")
            validate_spread_success_linkage(linked, attempt)


class SpreadEvidenceRepository:
    """Two-file local repository with no default operational path."""

    def __init__(self, observation_path: Path | str, attempt_path: Path | str) -> None:
        self.observation_path = Path(observation_path)
        self.attempt_path = Path(attempt_path)

    def observations(self) -> tuple[dict[str, Any], ...]:
        return read_spread_history(self.observation_path)

    def attempts(self) -> tuple[dict[str, Any], ...]:
        return read_spread_attempts(self.attempt_path)

    def validate(self) -> None:
        validate_spread_evidence_set(self.observations(), self.attempts())

    def append_observation(self, record: Mapping[str, Any]) -> bool:
        return append_spread_observation(self.observation_path, record)

    def append_attempt(self, record: Mapping[str, Any]) -> bool:
        if record.get("result") == "SUCCESS":
            linked = next(
                (
                    item for item in self.observations()
                    if item.get("observation_id") == record.get("observation_id")
                ),
                None,
            )
            if linked is None:
                raise SpreadAttemptError(
                    "successful spread attempt references missing observation"
                )
            validate_spread_success_linkage(linked, record)
        appended = append_spread_attempt(self.attempt_path, record)
        self.validate()
        return appended
