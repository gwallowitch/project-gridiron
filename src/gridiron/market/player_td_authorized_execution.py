"""Disabled production API and internal bounded ATTD execution engine.

Project Gridiron currently has no production-authorized Player ATTD transport
path. :func:`execute_registered_once` is an unconditional fail-closed public
tombstone and cannot be enabled by configuration, artifacts, or caller input.

The internal bounded execution engine is not an authentication or security
boundary. It exists for deterministic execution-state validation and synthetic
testing. Future real acquisition requires a separate explicitly authorized
design step. File flush and fsync provide best-effort local durability with
fail-closed replay semantics, not a physical power-loss guarantee.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gridiron.market.player_td_execution import (
    ExecutionBoundaryError,
    ExecutionStatus,
    PlayerTDRequest,
    SingleRequestTransport,
    TransportResult,
    load_strict_json,
    validate_execution_authorization,
    validate_resolution_artifact,
)
from gridiron.market.player_td_sample import (
    MAX_REQUEST_COUNT,
    validate_frozen_sample_manifest,
)

REGISTRY_VERSION = "step93i-attd-execution-registry-v1"
REGISTRY_FIELDS = {"schema_version", "registry_version", "entries", "registry_sha256"}
ENTRY_FIELDS = {
    "execution_authorization_id", "authorization_sha256", "manifest_sha256",
    "resolution_artifact_sha256", "provider", "authorization_file",
    "resolution_file", "state_file", "genesis_record_sha256",
}
COMMON_RECORD_FIELDS = {
    "sequence", "previous_record_sha256", "authorization_sha256",
    "manifest_sha256", "resolution_artifact_sha256", "state", "record_sha256",
}


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class _InternalExecutionContext:
    state_root: Path
    registry_sha256: str


@dataclass(frozen=True)
class _LedgerIdentity:
    device: int
    inode: int


def _inside_root(context: _InternalExecutionContext, relative: object) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ExecutionBoundaryError("registry path is invalid")
    if ".." in Path(relative).parts:
        raise ExecutionBoundaryError("registry path traversal is prohibited")
    root = context.state_root.resolve()
    target = (root / relative).resolve()
    if root not in target.parents:
        raise ExecutionBoundaryError("registry path escapes state root")
    cursor = target
    while cursor != root:
        if cursor.is_symlink():
            raise ExecutionBoundaryError("registry path cannot traverse a symlink")
        cursor = cursor.parent
    return target


def canonical_state_name(authorization_sha256: str) -> str:
    return f"states/{authorization_sha256}.jsonl"


def build_genesis_record(
    authorization: Mapping[str, Any], manifest: Mapping[str, Any], resolution: Mapping[str, Any]
) -> dict[str, Any]:
    base = {
        "sequence": 0,
        "previous_record_sha256": "0" * 64,
        "authorization_sha256": authorization["authorization_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
        "resolution_artifact_sha256": resolution["artifact_sha256"],
        "state": "AUTHORIZED",
        "execution_authorization_id": authorization["execution_authorization_id"],
        "sample_item_ids": authorization["sample_item_ids"],
    }
    return {**base, "record_sha256": _digest(base)}


def _internal_execution_context(
    state_root: Path, registry_sha256: str
) -> _InternalExecutionContext:
    """Build non-authorizing context for offline state-machine validation."""
    return _InternalExecutionContext(state_root.resolve(), registry_sha256)


def _registry(
    context: _InternalExecutionContext,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = _inside_root(context, "approval_registry.json")
    registry = load_strict_json(path)
    if not isinstance(registry, dict) or set(registry) != REGISTRY_FIELDS:
        raise ExecutionBoundaryError("approval registry schema is invalid")
    material = dict(registry)
    claimed = material.pop("registry_sha256", None)
    if claimed != _digest(material) or claimed != context.registry_sha256:
        raise ExecutionBoundaryError("approval registry is not trusted")
    if registry.get("schema_version") != 1 or registry.get("registry_version") != REGISTRY_VERSION:
        raise ExecutionBoundaryError("approval registry version is invalid")
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ExecutionBoundaryError("approval registry has no entries")
    if any(not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS for entry in entries):
        raise ExecutionBoundaryError("approval registry entry is invalid")
    ids = [entry["execution_authorization_id"] for entry in entries]
    hashes = [entry["authorization_sha256"] for entry in entries]
    if len(ids) != len(set(ids)) or len(hashes) != len(set(hashes)):
        raise ExecutionBoundaryError("approval registry identities are duplicated")
    return registry, entries


def _record(previous: Mapping[str, Any], state: str, **details: Any) -> dict[str, Any]:
    base = {
        "sequence": previous["sequence"] + 1,
        "previous_record_sha256": previous["record_sha256"],
        "authorization_sha256": previous["authorization_sha256"],
        "manifest_sha256": previous["manifest_sha256"],
        "resolution_artifact_sha256": previous["resolution_artifact_sha256"],
        "state": state,
        **details,
    }
    return {**base, "record_sha256": _digest(base)}


def _same_file_identity(descriptor_stat: os.stat_result, path_stat: os.stat_result) -> bool:
    return (
        descriptor_stat.st_dev == path_stat.st_dev
        and descriptor_stat.st_ino == path_stat.st_ino
    )


def _open_validated_ledger(
    path: Path,
    identity: _LedgerIdentity,
    expected_records: Sequence[Mapping[str, Any]],
):
    """Open an existing ledger and bind it to the exact expected chain."""
    flags = os.O_RDWR | os.O_APPEND | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError as exc:
        raise ExecutionBoundaryError("canonical execution state disappeared") from exc
    try:
        handle = os.fdopen(descriptor, "r+b", buffering=0)
    except Exception:
        os.close(descriptor)
        raise
    try:
        descriptor_stat = os.fstat(handle.fileno())
        try:
            path_stat = path.stat(follow_symlinks=False)
        except FileNotFoundError as exc:
            raise ExecutionBoundaryError("canonical execution state disappeared") from exc
        if (
            path.is_symlink()
            or not _same_file_identity(descriptor_stat, path_stat)
            or descriptor_stat.st_dev != identity.device
            or descriptor_stat.st_ino != identity.inode
        ):
            raise ExecutionBoundaryError("canonical execution state was replaced")
        handle.seek(0)
        if _records_from_bytes(handle.read()) != [dict(record) for record in expected_records]:
            raise ExecutionBoundaryError("canonical execution state lost continuity")
        return handle
    except Exception:
        handle.close()
        raise


def _assert_ledger_continuity(
    path: Path,
    identity: _LedgerIdentity,
    expected_records: Sequence[Mapping[str, Any]],
) -> None:
    with _open_validated_ledger(path, identity, expected_records):
        pass


def _append_existing(
    path: Path,
    identity: _LedgerIdentity,
    expected_records: Sequence[Mapping[str, Any]],
    record: Mapping[str, Any],
) -> None:
    encoded = (_canonical(record) + "\n").encode()
    with _open_validated_ledger(path, identity, expected_records) as handle:
        handle.seek(0, os.SEEK_END)
        handle.write(encoded)
        os.fsync(handle.fileno())
        descriptor_stat = os.fstat(handle.fileno())
        try:
            path_stat = path.stat(follow_symlinks=False)
        except FileNotFoundError as exc:
            raise ExecutionBoundaryError("canonical execution state disappeared") from exc
        if (
            not _same_file_identity(descriptor_stat, path_stat)
            or descriptor_stat.st_dev != identity.device
            or descriptor_stat.st_ino != identity.inode
        ):
            raise ExecutionBoundaryError("canonical execution state changed during append")
        handle.seek(0)
        expected_after = [*expected_records, dict(record)]
        if _records_from_bytes(handle.read()) != expected_after:
            raise ExecutionBoundaryError("canonical execution state append is incomplete")


def _records_from_bytes(raw: bytes) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExecutionBoundaryError("ledger encoding is invalid") from exc
    records = []
    for line in text.splitlines():
        value = json.loads(
            line, object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
        if not isinstance(value, dict):
            raise ExecutionBoundaryError("ledger record is malformed")
        records.append(value)
    if not records:
        raise ExecutionBoundaryError("ledger is empty")
    return records


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.is_symlink():
        raise ExecutionBoundaryError("expected canonical execution state is missing")
    return _records_from_bytes(path.read_bytes())


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExecutionBoundaryError(f"duplicate ledger key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ExecutionBoundaryError(f"non-finite JSON constant is prohibited: {value}")


def validate_ledger(
    records: Sequence[Mapping[str, Any]],
    entry: Mapping[str, Any],
    authorization: Mapping[str, Any],
) -> ExecutionStatus:
    expected_items = list(authorization["sample_item_ids"])
    completed: list[str] = []
    failed: list[str] = []
    indeterminate: list[str] = []
    attempted_index = 0
    pending: tuple[str, str] | None = None
    phase = "AUTHORIZED"
    terminal = False
    previous_hash = "0" * 64
    allowed_extra = {
        "AUTHORIZED": {"execution_authorization_id", "sample_item_ids"},
        "STARTED": set(),
        "ITEM_ATTEMPTED": {"sample_item_id", "attempt_id"},
        "ITEM_SUCCEEDED": {"sample_item_id", "attempt_id"},
        "ITEM_FAILED": {"sample_item_id", "attempt_id"},
        "FAILED_PARTIAL": {"reason"},
        "COMPLETED": set(),
    }
    for sequence, raw in enumerate(records):
        record = dict(raw)
        state = record.get("state")
        if state not in allowed_extra or set(record) != COMMON_RECORD_FIELDS | allowed_extra[state]:
            raise ExecutionBoundaryError("ledger record schema or state is invalid")
        material = dict(record)
        claimed = material.pop("record_sha256", None)
        if claimed != _digest(material):
            raise ExecutionBoundaryError("ledger record hash is invalid")
        if (
            record["sequence"] != sequence
            or record["previous_record_sha256"] != previous_hash
            or record["authorization_sha256"] != entry["authorization_sha256"]
            or record["manifest_sha256"] != entry["manifest_sha256"]
            or record["resolution_artifact_sha256"] != entry["resolution_artifact_sha256"]
            or terminal
        ):
            raise ExecutionBoundaryError("ledger chain or authority is invalid")
        previous_hash = claimed
        if sequence == 0:
            if (
                state != "AUTHORIZED"
                or record["execution_authorization_id"] != entry["execution_authorization_id"]
                or record["sample_item_ids"] != expected_items
                or claimed != entry["genesis_record_sha256"]
            ):
                raise ExecutionBoundaryError("ledger genesis is invalid")
            continue
        if state == "STARTED":
            if phase != "AUTHORIZED":
                raise ExecutionBoundaryError("STARTED transition is invalid")
            phase = "STARTED"
        elif state == "ITEM_ATTEMPTED":
            if phase not in {"STARTED", "ITEM_RESOLVED"} or pending is not None:
                raise ExecutionBoundaryError("ITEM_ATTEMPTED transition is invalid")
            if attempted_index >= len(expected_items) or record["sample_item_id"] != expected_items[attempted_index]:
                raise ExecutionBoundaryError("attempted sample order is invalid")
            expected_attempt = _digest({
                "authorization_sha256": entry["authorization_sha256"],
                "sample_item_id": record["sample_item_id"],
            })
            if record["attempt_id"] != expected_attempt:
                raise ExecutionBoundaryError("attempt identity is invalid")
            pending = (record["sample_item_id"], record["attempt_id"])
            indeterminate.append(record["sample_item_id"])
            attempted_index += 1
            phase = "ITEM_ATTEMPTED"
        elif state in {"ITEM_SUCCEEDED", "ITEM_FAILED"}:
            if pending != (record["sample_item_id"], record["attempt_id"]):
                raise ExecutionBoundaryError("item result has no matching attempt")
            indeterminate.remove(record["sample_item_id"])
            (completed if state == "ITEM_SUCCEEDED" else failed).append(record["sample_item_id"])
            pending = None
            phase = "ITEM_RESOLVED"
        elif state == "FAILED_PARTIAL":
            if phase not in {"ITEM_ATTEMPTED", "ITEM_RESOLVED"}:
                raise ExecutionBoundaryError("FAILED_PARTIAL transition is invalid")
            terminal = True
            phase = state
        elif state == "COMPLETED":
            if phase != "ITEM_RESOLVED" or len(completed) != MAX_REQUEST_COUNT or failed or pending:
                raise ExecutionBoundaryError("COMPLETED transition is impossible")
            terminal = True
            phase = state
        else:
            raise ExecutionBoundaryError("ledger transition is invalid")
    untouched = expected_items[attempted_index:]
    return ExecutionStatus(phase, tuple(completed), tuple(failed), tuple(indeterminate), tuple(untouched))


def _authority(
    context: _InternalExecutionContext, authorization_id: str
) -> tuple[dict[str, Any], ...]:
    _, entries = _registry(context)
    matches = [entry for entry in entries if entry["execution_authorization_id"] == authorization_id]
    if len(matches) != 1:
        raise ExecutionBoundaryError("execution authorization is not registered")
    entry = matches[0]
    expected_state = canonical_state_name(entry["authorization_sha256"])
    if entry["state_file"] != expected_state:
        raise ExecutionBoundaryError("registry state location is noncanonical")
    authorization = load_strict_json(_inside_root(context, entry["authorization_file"]))
    resolution = load_strict_json(_inside_root(context, entry["resolution_file"]))
    state_path = _inside_root(context, entry["state_file"])
    try:
        state_before = state_path.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise ExecutionBoundaryError("expected canonical execution state is missing") from exc
    records = _read_records(state_path)
    try:
        state_after = state_path.stat(follow_symlinks=False)
    except FileNotFoundError as exc:
        raise ExecutionBoundaryError("expected canonical execution state is missing") from exc
    if not _same_file_identity(state_before, state_after):
        raise ExecutionBoundaryError("canonical execution state changed during validation")
    identity = _LedgerIdentity(state_after.st_dev, state_after.st_ino)
    return entry, authorization, resolution, state_path, identity, records


def _execute_bounded_internal_once(
    context: _InternalExecutionContext,
    authorization_id: str,
    manifest: Mapping[str, Any],
    schedule: object,
    provenance: Mapping[str, Any],
    transport: SingleRequestTransport,
) -> tuple[TransportResult, ...]:
    manifest = json.loads(_canonical(manifest))
    schedule = json.loads(_canonical(schedule))
    provenance = json.loads(_canonical(provenance))
    validate_frozen_sample_manifest(manifest, schedule, provenance)
    entry, authorization, resolution, state_path, identity, records = _authority(
        context, authorization_id
    )
    validate_resolution_artifact(resolution, manifest)
    validate_execution_authorization(authorization, manifest, resolution)
    if (
        entry["manifest_sha256"] != manifest["manifest_sha256"]
        or entry["resolution_artifact_sha256"] != resolution["artifact_sha256"]
        or entry["authorization_sha256"] != authorization["authorization_sha256"]
    ):
        raise ExecutionBoundaryError("registry authority binding is invalid")
    status = validate_ledger(records, entry, authorization)
    if status.state != "AUTHORIZED":
        raise ExecutionBoundaryError("execution authorization is already started or consumed")
    claim_path = _inside_root(
        context, f"claims/{entry['authorization_sha256']}.claimed"
    )
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with claim_path.open("xb", buffering=0) as handle:
            handle.write(entry["authorization_sha256"].encode())
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ExecutionBoundaryError("execution authorization is already claimed") from exc
    expected_records = list(records)
    previous = expected_records[-1]
    started = _record(previous, "STARTED")
    _append_existing(state_path, identity, expected_records, started)
    expected_records.append(started)
    previous = started
    results: list[TransportResult] = []
    for item, binding in zip(manifest["items"], resolution["bindings"], strict=True):
        attempt_id = _digest({
            "authorization_sha256": entry["authorization_sha256"],
            "sample_item_id": item["sample_item_id"],
        })
        attempted = _record(
            previous, "ITEM_ATTEMPTED", sample_item_id=item["sample_item_id"],
            attempt_id=attempt_id,
        )
        _append_existing(state_path, identity, expected_records, attempted)
        expected_records.append(attempted)
        previous = attempted
        request = PlayerTDRequest(
            item["sample_item_id"], binding["provider_event_id"], item["canonical_game_id"],
            item["requested_snapshot_at"], item["market"], tuple(item["books"]),
            item["region"], item["odds_format"],
        )
        _assert_ledger_continuity(state_path, identity, expected_records)
        try:
            result = transport.send_once(request)
        except Exception as exc:
            failed = _record(previous, "FAILED_PARTIAL", reason="INDETERMINATE")
            try:
                _append_existing(state_path, identity, expected_records, failed)
            except ExecutionBoundaryError as continuity_error:
                raise ExecutionBoundaryError(
                    "ledger continuity was lost during transport; outcome is indeterminate",
                    attempted=len(results) + 1,
                ) from continuity_error
            expected_records.append(failed)
            raise ExecutionBoundaryError(
                "transport outcome is indeterminate", attempted=len(results) + 1
            ) from exc
        results.append(result)
        expands = isinstance(result, TransportResult) and (
            result.underlying_request_count != 1 or result.retry_required
            or result.pagination_required or result.fallback_required
            or result.discovery_required
        )
        terminal_state = "ITEM_SUCCEEDED"
        if not isinstance(result, TransportResult) or expands or not result.succeeded:
            terminal_state = "ITEM_FAILED"
        item_result = _record(
            previous, terminal_state, sample_item_id=item["sample_item_id"],
            attempt_id=attempt_id,
        )
        try:
            _append_existing(state_path, identity, expected_records, item_result)
        except ExecutionBoundaryError as exc:
            raise ExecutionBoundaryError(
                "ledger continuity was lost after transport; outcome is indeterminate",
                attempted=len(results),
            ) from exc
        expected_records.append(item_result)
        previous = item_result
        if terminal_state == "ITEM_FAILED":
            failed = _record(previous, "FAILED_PARTIAL", reason="FAILED")
            _append_existing(state_path, identity, expected_records, failed)
            expected_records.append(failed)
            raise ExecutionBoundaryError("acquisition failed closed", attempted=len(results))
    completed = _record(previous, "COMPLETED")
    _append_existing(state_path, identity, expected_records, completed)
    return tuple(results)


def execute_registered_once(
    authorization_id: str,
    manifest: Mapping[str, Any],
    schedule: object,
    provenance: Mapping[str, Any],
    transport: SingleRequestTransport,
) -> tuple[TransportResult, ...]:
    """Fail closed: production Player ATTD acquisition is not authorized."""
    del authorization_id, manifest, schedule, provenance, transport
    raise ExecutionBoundaryError(
        "production Player ATTD transport is disabled; no activation mechanism exists"
    )


__all__ = [
    "ExecutionBoundaryError",
    "build_genesis_record",
    "canonical_state_name",
    "execute_registered_once",
    "validate_ledger",
]
