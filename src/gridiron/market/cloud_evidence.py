"""Transactional non-prospective cloud-candidate evidence contracts.

Google dependencies are deliberately optional.  The in-memory implementation is
the executable contract used by unit tests; ``FirestoreEvidenceRepository`` uses
the same state transitions against a Firestore client supplied by the caller.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from gridiron.market.collection_attempts import validate_collection_attempt
from gridiron.market.operational_history import (
    _validate_record_semantics,
    canonical_json,
)
from gridiron.market.operational_totals import (
    _validate_record as validate_totals_record,
)
from gridiron.market.totals_collection_attempts import (
    _validate as validate_totals_attempt,
)

SCHEMA_VERSION = 1
CLASSIFICATION = "NON_PROSPECTIVE_CLOUD_CANDIDATE"
MAX_RAW_DOCUMENT_BYTES = 900_000
MARKET_TYPES = {"MONEYLINE", "TOTALS"}
SLOT_STATES = {
    "LEASED",
    "RAW_CAPTURED",
    "TERMINAL_SUCCESS",
    "TERMINAL_FAILED_OR_MISSED",
}
CANONICAL_COLLECTIONS = {
    "MONEYLINE": ("moneyline_observations", "moneyline_attempts"),
    "TOTALS": ("totals_observations", "totals_attempts"),
}


class CloudEvidenceError(ValueError):
    """Cloud-candidate state is malformed, conflicting, or unauthorized."""


class LeaseUnavailableError(CloudEvidenceError):
    """A slot is terminal or has an unexpired lease owned elsewhere."""


class StaleLeaseError(CloudEvidenceError):
    """A caller no longer owns the current lease generation."""


class ImmutableConflictError(CloudEvidenceError):
    """An immutable identity already exists with different content."""


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None:
        raise CloudEvidenceError(f"{field} must include a timezone")
    return value.astimezone(UTC)


def _sha(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def logical_slot_id(game_id: str, market_type: str, target_label: str) -> str:
    """Return the frozen logical slot identity."""
    if not game_id or market_type not in MARKET_TYPES or not target_label:
        raise CloudEvidenceError("invalid logical slot identity")
    return _sha(
        {
            "game_id": game_id,
            "market_type": market_type,
            "target_label": target_label,
        }
    )


def build_slot(
    *,
    game_id: str,
    market_type: str,
    target_label: str,
    kickoff_at: str,
    target_minutes: int,
    lower_bound_minutes: int,
    upper_bound_minutes: int,
) -> dict[str, Any]:
    if not (lower_bound_minutes <= target_minutes <= upper_bound_minutes):
        raise CloudEvidenceError("slot target must fall inside frozen bounds")
    identity = logical_slot_id(game_id, market_type, target_label)
    return {
        "schema_version": SCHEMA_VERSION,
        "classification": CLASSIFICATION,
        "slot_id": identity,
        "game_id": game_id,
        "market_type": market_type,
        "target_label": target_label,
        "kickoff_at": kickoff_at,
        "target_minutes": target_minutes,
        "lower_bound_minutes": lower_bound_minutes,
        "upper_bound_minutes": upper_bound_minutes,
    }


@dataclass(frozen=True)
class LeaseToken:
    slot_id: str
    owner: str
    epoch: int


def sanitize_provider_metadata(value: object) -> object:
    """Reject credential-shaped keys/URLs rather than attempting redaction."""
    forbidden = {"apikey", "api_key", "authorization", "credential", "secret"}
    if isinstance(value, Mapping):
        cleaned: dict[str, object] = {}
        for raw_key, child in value.items():
            key = str(raw_key)
            normalized = key.lower().replace("-", "_")
            if normalized in forbidden or any(word in normalized for word in forbidden):
                raise CloudEvidenceError("raw provider metadata contains a secret field")
            cleaned[key] = sanitize_provider_metadata(child)
        return cleaned
    if isinstance(value, list):
        return [sanitize_provider_metadata(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_provider_metadata(item) for item in value]
    if isinstance(value, str) and ("apikey=" in value.lower() or "api_key=" in value.lower()):
        raise CloudEvidenceError("raw provider metadata contains a credential-bearing URL")
    return value


def build_raw_response(
    *,
    provider: str,
    lane: str,
    product: str,
    requested_books: Iterable[str],
    fetched_at: datetime,
    payload: object,
    slot_ids: Iterable[str],
    parser_version: str,
) -> dict[str, Any]:
    if lane not in MARKET_TYPES:
        raise CloudEvidenceError("invalid raw-response lane")
    clean_payload = sanitize_provider_metadata(payload)
    slots = sorted(set(slot_ids))
    if not slots:
        raise CloudEvidenceError("raw response must bind at least one slot")
    fetched = _utc(fetched_at, "fetched_at").isoformat().replace("+00:00", "Z")
    payload_sha = _sha(clean_payload)
    base = {
        "schema_version": SCHEMA_VERSION,
        "classification": CLASSIFICATION,
        "provider": provider,
        "lane": lane,
        "product": product,
        "requested_books": sorted(set(requested_books)),
        "fetched_at": fetched,
        "payload": clean_payload,
        "payload_sha256": payload_sha,
        "slot_ids": slots,
        "parser_version": parser_version,
    }
    if len(canonical_json(base).encode("utf-8")) > MAX_RAW_DOCUMENT_BYTES:
        raise CloudEvidenceError(
            "raw provider response requires deterministic Firestore chunking"
        )
    return {**base, "raw_response_id": _sha(base)}


def validate_raw_response(record: Mapping[str, Any]) -> None:
    material = dict(record)
    identity = material.pop("raw_response_id", None)
    if identity != _sha(material):
        raise CloudEvidenceError("invalid raw-response identity")
    if record.get("classification") != CLASSIFICATION:
        raise CloudEvidenceError("invalid raw-response classification")
    if record.get("payload_sha256") != _sha(record.get("payload")):
        raise CloudEvidenceError("raw provider payload is corrupt")
    sanitize_provider_metadata(record)


def validate_canonical_identity(record: Mapping[str, Any], identity_field: str) -> None:
    material = dict(record)
    identity = material.pop(identity_field, None)
    if identity != _sha(material):
        raise CloudEvidenceError(f"invalid {identity_field}")


class OperationalEvidenceRepository(Protocol):
    def inspect_slot(self, slot_id: str) -> dict[str, Any] | None: ...
    def acquire_lease(
        self, slot: Mapping[str, Any], *, owner: str, now: datetime, ttl: timedelta
    ) -> LeaseToken: ...
    def checkpoint_raw(
        self, leases: Iterable[LeaseToken], raw_response: Mapping[str, Any]
    ) -> None: ...
    def commit_success(
        self,
        lease: LeaseToken,
        *,
        raw_response_id: str,
        observation: Mapping[str, Any],
        attempt: Mapping[str, Any],
    ) -> None: ...
    def commit_terminal_attempt(
        self, lease: LeaseToken, *, attempt: Mapping[str, Any]
    ) -> None: ...
    def enumerate_evidence(self, collection: str) -> tuple[dict[str, Any], ...]: ...
    def enumerate_slots(self) -> tuple[dict[str, Any], ...]: ...
    def get_raw_response(self, raw_response_id: str) -> dict[str, Any]: ...


class InMemoryEvidenceRepository:
    """Faithful transactional state-machine fake; not proof of Firestore behavior."""

    def __init__(self) -> None:
        self.slots: dict[str, dict[str, Any]] = {}
        self.raw_responses: dict[str, dict[str, Any]] = {}
        self.collections: dict[str, dict[str, dict[str, Any]]] = {
            name: {} for pair in CANONICAL_COLLECTIONS.values() for name in pair
        }

    def inspect_slot(self, slot_id: str) -> dict[str, Any] | None:
        value = self.slots.get(slot_id)
        return None if value is None else deepcopy(value)

    def acquire_lease(
        self, slot: Mapping[str, Any], *, owner: str, now: datetime, ttl: timedelta
    ) -> LeaseToken:
        current_time = _utc(now, "lease time")
        if not owner or ttl <= timedelta(0):
            raise CloudEvidenceError("lease owner and positive TTL are required")
        slot_id = str(slot["slot_id"])
        if slot_id != logical_slot_id(
            str(slot["game_id"]), str(slot["market_type"]), str(slot["target_label"])
        ):
            raise CloudEvidenceError("slot identity is invalid")
        current = self.slots.get(slot_id)
        epoch = 1
        if current is not None:
            if current["state"].startswith("TERMINAL_"):
                raise LeaseUnavailableError("terminal slot cannot be reacquired")
            expires = datetime.fromisoformat(str(current["lease_expires_at"]))
            if expires > current_time:
                raise LeaseUnavailableError("slot lease is still active")
            epoch = int(current["lease_epoch"]) + 1
        acquired = current_time.isoformat().replace("+00:00", "Z")
        expires = (current_time + ttl).isoformat().replace("+00:00", "Z")
        retained_raw = None if current is None else current.get("raw_response_id")
        retained_state = (
            "RAW_CAPTURED"
            if current is not None and current.get("state") == "RAW_CAPTURED"
            else "LEASED"
        )
        self.slots[slot_id] = {
            **dict(slot),
            "state": retained_state,
            "lease_owner": owner,
            "lease_epoch": epoch,
            "lease_acquired_at": acquired,
            "lease_expires_at": expires,
            "raw_response_id": retained_raw,
            "observation_id": None,
            "attempt_id": None,
            "terminal_classification": None,
        }
        return LeaseToken(slot_id, owner, epoch)

    def _owned(self, lease: LeaseToken, required_state: str | None = None) -> dict[str, Any]:
        slot = self.slots.get(lease.slot_id)
        if (
            slot is None
            or slot.get("lease_owner") != lease.owner
            or slot.get("lease_epoch") != lease.epoch
            or (required_state is not None and slot.get("state") != required_state)
        ):
            raise StaleLeaseError("lease owner or epoch is stale")
        return slot

    @staticmethod
    def _create_exact(
        collection: dict[str, dict[str, Any]], identity: str, record: Mapping[str, Any]
    ) -> None:
        existing = collection.get(identity)
        candidate = deepcopy(dict(record))
        if existing is not None and existing != candidate:
            raise ImmutableConflictError("immutable identity has conflicting content")
        collection[identity] = candidate

    def checkpoint_raw(
        self, leases: Iterable[LeaseToken], raw_response: Mapping[str, Any]
    ) -> None:
        validate_raw_response(raw_response)
        tokens = tuple(leases)
        bound = set(raw_response["slot_ids"])
        if {token.slot_id for token in tokens} != bound:
            raise CloudEvidenceError("raw response slot binding is incomplete")
        for token in tokens:
            slot = self._owned(token)
            if slot["state"] == "RAW_CAPTURED" and slot["raw_response_id"] == raw_response["raw_response_id"]:
                continue
            if slot["state"] != "LEASED":
                raise StaleLeaseError("slot cannot checkpoint raw evidence")
        raw_id = str(raw_response["raw_response_id"])
        self._create_exact(self.raw_responses, raw_id, raw_response)
        for token in tokens:
            slot = self.slots[token.slot_id]
            slot["state"] = "RAW_CAPTURED"
            slot["raw_response_id"] = raw_id

    def commit_success(
        self,
        lease: LeaseToken,
        *,
        raw_response_id: str,
        observation: Mapping[str, Any],
        attempt: Mapping[str, Any],
    ) -> None:
        slot = self._owned(lease)
        if slot["state"] == "TERMINAL_SUCCESS":
            if (
                slot.get("raw_response_id") == raw_response_id
                and slot.get("observation_id") == observation.get("observation_id")
                and slot.get("attempt_id") == attempt.get("attempt_id")
            ):
                return
            raise ImmutableConflictError("terminal success conflicts with retry")
        if slot["state"] != "RAW_CAPTURED":
            raise StaleLeaseError("slot has not checkpointed raw evidence")
        if slot.get("raw_response_id") != raw_response_id:
            raise CloudEvidenceError("success commit is bound to the wrong raw response")
        validate_raw_response(self.raw_responses[raw_response_id])
        validate_canonical_identity(observation, "observation_id")
        validate_canonical_identity(attempt, "attempt_id")
        observation_id = str(observation["observation_id"])
        attempt_id = str(attempt["attempt_id"])
        if attempt.get("observation_id") != observation_id:
            raise CloudEvidenceError("attempt does not link committed observation")
        observation_collection, attempt_collection = CANONICAL_COLLECTIONS[slot["market_type"]]
        staged_observations = deepcopy(self.collections[observation_collection])
        staged_attempts = deepcopy(self.collections[attempt_collection])
        self._create_exact(staged_observations, observation_id, observation)
        self._create_exact(staged_attempts, attempt_id, attempt)
        self.collections[observation_collection] = staged_observations
        self.collections[attempt_collection] = staged_attempts
        slot.update(
            state="TERMINAL_SUCCESS",
            observation_id=observation_id,
            attempt_id=attempt_id,
            terminal_classification="SUCCESS",
        )

    def commit_terminal_attempt(
        self, lease: LeaseToken, *, attempt: Mapping[str, Any]
    ) -> None:
        slot = self._owned(lease)
        if slot["state"] == "TERMINAL_FAILED_OR_MISSED":
            if slot.get("attempt_id") == attempt.get("attempt_id"):
                return
            raise ImmutableConflictError("terminal attempt conflicts with retry")
        if slot["state"] not in {"LEASED", "RAW_CAPTURED"}:
            raise StaleLeaseError("slot cannot accept a terminal attempt")
        validate_canonical_identity(attempt, "attempt_id")
        if attempt.get("observation_id") is not None:
            raise CloudEvidenceError("failed or missed attempt cannot link an observation")
        _, attempt_collection = CANONICAL_COLLECTIONS[slot["market_type"]]
        attempt_id = str(attempt["attempt_id"])
        staged = deepcopy(self.collections[attempt_collection])
        self._create_exact(staged, attempt_id, attempt)
        self.collections[attempt_collection] = staged
        slot.update(
            state="TERMINAL_FAILED_OR_MISSED",
            attempt_id=attempt_id,
            terminal_classification=str(attempt.get("result")),
        )

    def enumerate_evidence(self, collection: str) -> tuple[dict[str, Any], ...]:
        if collection not in self.collections:
            raise CloudEvidenceError("unknown canonical evidence collection")
        return tuple(deepcopy(row) for row in self.collections[collection].values())

    def enumerate_slots(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(row) for row in self.slots.values())

    def get_raw_response(self, raw_response_id: str) -> dict[str, Any]:
        record = self.raw_responses.get(raw_response_id)
        if record is None:
            raise CloudEvidenceError("raw response is missing")
        validate_raw_response(record)
        return deepcopy(record)


class FirestoreEvidenceRepository:
    """Firestore adapter. Importing this module never imports Google packages."""

    def __init__(self, client: Any, *, namespace: str = "candidate_v1") -> None:
        self.client = client
        self.namespace = namespace

    @classmethod
    def from_default_client(cls) -> FirestoreEvidenceRepository:
        try:
            from google.cloud import firestore
        except ImportError as exc:
            raise CloudEvidenceError(
                "Firestore support requires the optional cloud dependencies"
            ) from exc
        return cls(firestore.Client())

    def _collection(self, name: str) -> Any:
        return self.client.collection(f"{self.namespace}_{name}")

    @staticmethod
    def _transactional(function: Any) -> Any:
        try:
            from google.cloud.firestore_v1 import transactional
        except ImportError as exc:
            raise CloudEvidenceError(
                "Firestore support requires the optional cloud dependencies"
            ) from exc
        return transactional(function)

    def inspect_slot(self, slot_id: str) -> dict[str, Any] | None:
        snapshot = self._collection("collection_slots").document(slot_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def acquire_lease(
        self, slot: Mapping[str, Any], *, owner: str, now: datetime, ttl: timedelta
    ) -> LeaseToken:
        current_time = _utc(now, "lease time")
        reference = self._collection("collection_slots").document(str(slot["slot_id"]))
        transaction = self.client.transaction()

        @self._transactional
        def apply(tx: Any) -> LeaseToken:
            snapshot = reference.get(transaction=tx)
            current = snapshot.to_dict() if snapshot.exists else None
            epoch = 1
            if current is not None:
                if str(current["state"]).startswith("TERMINAL_"):
                    raise LeaseUnavailableError("terminal slot cannot be reacquired")
                expires = datetime.fromisoformat(str(current["lease_expires_at"]))
                if expires > current_time:
                    raise LeaseUnavailableError("slot lease is still active")
                epoch = int(current["lease_epoch"]) + 1
            retained_raw = None if current is None else current.get("raw_response_id")
            retained_state = (
                "RAW_CAPTURED"
                if current is not None and current.get("state") == "RAW_CAPTURED"
                else "LEASED"
            )
            record = {
                **dict(slot),
                "state": retained_state,
                "lease_owner": owner,
                "lease_epoch": epoch,
                "lease_acquired_at": current_time.isoformat().replace("+00:00", "Z"),
                "lease_expires_at": (current_time + ttl).isoformat().replace("+00:00", "Z"),
                "raw_response_id": retained_raw,
                "observation_id": None,
                "attempt_id": None,
                "terminal_classification": None,
            }
            tx.set(reference, record)
            return LeaseToken(str(slot["slot_id"]), owner, epoch)

        try:
            return apply(transaction)
        except LeaseUnavailableError:
            raise
        except ValueError as exc:
            # The official emulator can exhaust transaction retries under a
            # pessimistic lock before the callback observes the winning lease.
            # Re-read only to classify a demonstrated competing slot; never
            # manufacture success after an otherwise unexplained failure.
            try:
                from google.api_core.exceptions import Aborted
            except ImportError:  # pragma: no cover - Firestore import already required.
                Aborted = ()  # type: ignore[assignment,misc]
            if isinstance(exc.__cause__, Aborted) and self.inspect_slot(
                str(slot["slot_id"])
            ) is not None:
                raise LeaseUnavailableError(
                    "slot lease was acquired by a competing transaction"
                ) from exc
            raise CloudEvidenceError("lease transaction failed after retries") from exc

    def _require_owned(self, tx: Any, lease: LeaseToken, state: str | None = None) -> tuple[Any, dict[str, Any]]:
        reference = self._collection("collection_slots").document(lease.slot_id)
        snapshot = reference.get(transaction=tx)
        current = snapshot.to_dict() if snapshot.exists else None
        if (
            current is None
            or current.get("lease_owner") != lease.owner
            or current.get("lease_epoch") != lease.epoch
            or (state is not None and current.get("state") != state)
        ):
            raise StaleLeaseError("lease owner or epoch is stale")
        return reference, current

    @staticmethod
    def _create_or_validate(tx: Any, reference: Any, snapshot: Any, record: Mapping[str, Any]) -> None:
        if snapshot.exists:
            if snapshot.to_dict() != dict(record):
                raise ImmutableConflictError("immutable identity has conflicting content")
        else:
            tx.create(reference, dict(record))

    def checkpoint_raw(self, leases: Iterable[LeaseToken], raw_response: Mapping[str, Any]) -> None:
        validate_raw_response(raw_response)
        tokens = tuple(leases)
        if {token.slot_id for token in tokens} != set(raw_response["slot_ids"]):
            raise CloudEvidenceError("raw response slot binding is incomplete")
        raw_ref = self._collection("raw_provider_responses").document(str(raw_response["raw_response_id"]))
        transaction = self.client.transaction()

        @self._transactional
        def apply(tx: Any) -> None:
            owned = [self._require_owned(tx, token) for token in tokens]
            raw_snapshot = raw_ref.get(transaction=tx)
            self._create_or_validate(tx, raw_ref, raw_snapshot, raw_response)
            for reference, current in owned:
                if current["state"] == "RAW_CAPTURED" and current["raw_response_id"] == raw_response["raw_response_id"]:
                    continue
                if current["state"] != "LEASED":
                    raise StaleLeaseError("slot cannot checkpoint raw evidence")
                tx.set(reference, {**current, "state": "RAW_CAPTURED", "raw_response_id": raw_response["raw_response_id"]})

        apply(transaction)

    def commit_success(
        self, lease: LeaseToken, *, raw_response_id: str,
        observation: Mapping[str, Any], attempt: Mapping[str, Any],
    ) -> None:
        validate_canonical_identity(observation, "observation_id")
        validate_canonical_identity(attempt, "attempt_id")
        transaction = self.client.transaction()

        @self._transactional
        def apply(tx: Any) -> None:
            slot_ref, slot = self._require_owned(tx, lease)
            if slot["state"] == "TERMINAL_SUCCESS":
                if (
                    slot.get("raw_response_id") == raw_response_id
                    and slot.get("observation_id") == observation.get("observation_id")
                    and slot.get("attempt_id") == attempt.get("attempt_id")
                ):
                    return
                raise ImmutableConflictError("terminal success conflicts with retry")
            if slot["state"] != "RAW_CAPTURED":
                raise StaleLeaseError("slot has not checkpointed raw evidence")
            if slot.get("raw_response_id") != raw_response_id:
                raise CloudEvidenceError("success commit is bound to the wrong raw response")
            raw_ref = self._collection("raw_provider_responses").document(raw_response_id)
            raw_snapshot = raw_ref.get(transaction=tx)
            if not raw_snapshot.exists:
                raise CloudEvidenceError("bound raw response is missing")
            validate_raw_response(raw_snapshot.to_dict())
            observation_name, attempt_name = CANONICAL_COLLECTIONS[slot["market_type"]]
            observation_ref = self._collection(observation_name).document(str(observation["observation_id"]))
            attempt_ref = self._collection(attempt_name).document(str(attempt["attempt_id"]))
            observation_snapshot = observation_ref.get(transaction=tx)
            attempt_snapshot = attempt_ref.get(transaction=tx)
            self._create_or_validate(tx, observation_ref, observation_snapshot, observation)
            self._create_or_validate(tx, attempt_ref, attempt_snapshot, attempt)
            tx.set(slot_ref, {
                **slot,
                "state": "TERMINAL_SUCCESS",
                "observation_id": observation["observation_id"],
                "attempt_id": attempt["attempt_id"],
                "terminal_classification": "SUCCESS",
            })

        apply(transaction)

    def commit_terminal_attempt(self, lease: LeaseToken, *, attempt: Mapping[str, Any]) -> None:
        validate_canonical_identity(attempt, "attempt_id")
        transaction = self.client.transaction()

        @self._transactional
        def apply(tx: Any) -> None:
            slot_ref, slot = self._require_owned(tx, lease)
            if slot["state"] == "TERMINAL_FAILED_OR_MISSED":
                if slot.get("attempt_id") == attempt.get("attempt_id"):
                    return
                raise ImmutableConflictError("terminal attempt conflicts with retry")
            if slot["state"] not in {"LEASED", "RAW_CAPTURED"}:
                raise StaleLeaseError("slot cannot accept a terminal attempt")
            _, attempt_name = CANONICAL_COLLECTIONS[slot["market_type"]]
            attempt_ref = self._collection(attempt_name).document(str(attempt["attempt_id"]))
            snapshot = attempt_ref.get(transaction=tx)
            self._create_or_validate(tx, attempt_ref, snapshot, attempt)
            tx.set(slot_ref, {
                **slot,
                "state": "TERMINAL_FAILED_OR_MISSED",
                "attempt_id": attempt["attempt_id"],
                "terminal_classification": attempt.get("result"),
            })

        apply(transaction)

    def enumerate_evidence(self, collection: str) -> tuple[dict[str, Any], ...]:
        if collection not in {name for pair in CANONICAL_COLLECTIONS.values() for name in pair}:
            raise CloudEvidenceError("unknown canonical evidence collection")
        return tuple(snapshot.to_dict() for snapshot in self._collection(collection).stream())

    def enumerate_slots(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            snapshot.to_dict()
            for snapshot in self._collection("collection_slots").stream()
        )

    def get_raw_response(self, raw_response_id: str) -> dict[str, Any]:
        snapshot = self._collection("raw_provider_responses").document(raw_response_id).get()
        if not snapshot.exists:
            raise CloudEvidenceError("raw response is missing")
        record = snapshot.to_dict()
        validate_raw_response(record)
        return record


EXPORT_FILES = {
    "moneyline_observations": "market_history_v1.jsonl",
    "moneyline_attempts": "collection_attempts_v1.jsonl",
    "totals_observations": "totals_history_v1.jsonl",
    "totals_attempts": "totals_collection_attempts_v1.jsonl",
}


def _fsync_directory(path: Path) -> None:
    """Persist directory entries where the operating system supports it."""
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def export_jsonl_generation(
    repository: OperationalEvidenceRepository,
    *,
    cache_root: Path | str,
    generation_id: str,
) -> Path:
    """Publish one validated immutable local cache generation."""
    if not generation_id or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for character in generation_id):
        raise CloudEvidenceError("generation_id contains unsafe characters")
    root = Path(cache_root)
    generations = root / "generations"
    destination = generations / generation_id
    if destination.exists():
        raise CloudEvidenceError("cache generation already exists")
    temporary = generations / f".{generation_id}.tmp"
    temporary.mkdir(parents=True, exist_ok=False)
    try:
        exported: dict[str, list[dict[str, Any]]] = {}
        for collection, filename in EXPORT_FILES.items():
            rows = list(repository.enumerate_evidence(collection))
            identity_field = "observation_id" if collection.endswith("observations") else "attempt_id"
            seen: set[str] = set()
            for row in rows:
                validate_canonical_identity(row, identity_field)
                identity = str(row[identity_field])
                if identity in seen:
                    raise CloudEvidenceError("duplicate identity in cloud evidence")
                seen.add(identity)
                if collection == "moneyline_attempts":
                    validate_collection_attempt(row)
                elif collection == "moneyline_observations":
                    _validate_record_semantics(row)
                elif collection == "totals_observations":
                    validate_totals_record(row)
                else:
                    validate_totals_attempt(row)
            rows.sort(key=lambda row: str(row[identity_field]))
            exported[collection] = rows
            path = temporary / filename
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                for row in rows:
                    stream.write(canonical_json(row) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        _fsync_directory(temporary)
        observations = {
            row["observation_id"]
            for collection in ("moneyline_observations", "totals_observations")
            for row in exported[collection]
        }
        attempts = {
            row["attempt_id"]: row
            for collection in ("moneyline_attempts", "totals_attempts")
            for row in exported[collection]
        }
        for slot in repository.enumerate_slots():
            state = slot.get("state")
            if not str(state).startswith("TERMINAL_"):
                continue
            attempt = attempts.get(slot.get("attempt_id"))
            if attempt is None:
                raise CloudEvidenceError("terminal slot has no exported attempt")
            if state == "TERMINAL_SUCCESS":
                observation_id = slot.get("observation_id")
                if (
                    observation_id not in observations
                    or attempt.get("observation_id") != observation_id
                ):
                    raise CloudEvidenceError("successful slot linkage is invalid")
            elif attempt.get("observation_id") is not None:
                raise CloudEvidenceError("failed slot links an observation")
        temporary.rename(destination)
        _fsync_directory(generations)
        pointer_temp = root / "CURRENT.tmp"
        with pointer_temp.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(generation_id + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pointer_temp, root / "CURRENT")
        _fsync_directory(root)
        return destination
    except Exception:
        # An unpublished temporary directory contains no accepted cache generation.
        for path in temporary.glob("*") if temporary.exists() else ():
            path.unlink()
        if temporary.exists():
            temporary.rmdir()
        raise
