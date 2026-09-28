"""One-time, durable execution authority for the frozen ATTD sample."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from gridiron.market.player_td_sample import (
    MAX_REQUEST_COUNT,
)

AUTH_VERSION = "step93g-one-time-attd-execution-v1"
RESOLUTION_VERSION = "step93g-attd-event-resolution-v1"
PROVIDER = "the-odds-api"
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}\Z")


class ExecutionBoundaryError(RuntimeError):
    def __init__(self, message: str, *, attempted: int = 0) -> None:
        super().__init__(message)
        self.attempted = attempted


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExecutionBoundaryError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ExecutionBoundaryError(f"non-finite JSON constant is prohibited: {value}")


def strict_json_loads(raw: str) -> Any:
    try:
        return json.loads(
            raw, object_pairs_hook=_unique_pairs,
            parse_constant=_reject_nonfinite,
        )
    except json.JSONDecodeError as exc:
        raise ExecutionBoundaryError("authority JSON is malformed") from exc


def load_strict_json(path: Path | str) -> Any:
    source = Path(path)
    if source.is_symlink():
        raise ExecutionBoundaryError("authority path cannot be a symlink")
    return strict_json_loads(source.read_text(encoding="utf-8"))


def _snapshot(value: object) -> Any:
    try:
        return strict_json_loads(_canonical(value))
    except (TypeError, ValueError) as exc:
        raise ExecutionBoundaryError("authority is not canonical JSON") from exc


def _identity(value: object, field: str, maximum: int = 200) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or len(value) > maximum
        or IDENTITY.fullmatch(value) is None
    ):
        raise ExecutionBoundaryError(f"{field} is invalid")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not value:
        raise ExecutionBoundaryError(f"{field} is invalid")
    return value


RESOLUTION_FIELDS = {
    "schema_version", "artifact_version", "provider", "resolution_method",
    "resolution_source", "approved_by", "approval_status", "bindings",
    "artifact_sha256",
}
BINDING_FIELDS = {
    "sample_item_id", "provider_event_id", "canonical_game_id", "home_team",
    "away_team", "kickoff_at",
}
AUTH_FIELDS = {
    "schema_version", "authorization_version", "execution_authorization_id",
    "manifest_sha256", "resolution_artifact_sha256", "sample_item_ids",
    "provider_event_bindings", "maximum_acquisition_attempts",
    "authorization_sha256",
}


def build_resolution_artifact(
    manifest: Mapping[str, Any],
    event_ids: Sequence[str],
    *,
    resolution_method: str,
    resolution_source: str,
    approved_by: str,
) -> dict[str, Any]:
    if len(event_ids) != MAX_REQUEST_COUNT:
        raise ExecutionBoundaryError("exactly six event bindings are required")
    bindings = [
        {
            "sample_item_id": item["sample_item_id"],
            "provider_event_id": _identity(event_id, "provider_event_id"),
            "canonical_game_id": item["canonical_game_id"],
            "home_team": item["home_team"],
            "away_team": item["away_team"],
            "kickoff_at": item["kickoff_at"],
        }
        for item, event_id in zip(manifest["items"], event_ids, strict=True)
    ]
    base = {
        "schema_version": 1,
        "artifact_version": RESOLUTION_VERSION,
        "provider": PROVIDER,
        "resolution_method": _text(resolution_method, "resolution_method"),
        "resolution_source": _text(resolution_source, "resolution_source"),
        "approved_by": _text(approved_by, "approved_by"),
        "approval_status": "APPROVED",
        "bindings": bindings,
    }
    return {**base, "artifact_sha256": _digest(base)}


def validate_resolution_artifact(
    artifact: Mapping[str, Any], manifest: Mapping[str, Any]
) -> None:
    if set(artifact) != RESOLUTION_FIELDS:
        raise ExecutionBoundaryError("resolution artifact schema is invalid")
    material = dict(artifact)
    claimed = material.pop("artifact_sha256", None)
    if claimed != _digest(material):
        raise ExecutionBoundaryError("resolution artifact hash is invalid")
    if (
        artifact.get("schema_version") != 1
        or artifact.get("artifact_version") != RESOLUTION_VERSION
        or artifact.get("provider") != PROVIDER
        or artifact.get("approval_status") != "APPROVED"
    ):
        raise ExecutionBoundaryError("resolution artifact is not approved")
    for field in ("resolution_method", "resolution_source", "approved_by"):
        _text(artifact.get(field), field)
    bindings = artifact.get("bindings")
    if not isinstance(bindings, list) or len(bindings) != MAX_REQUEST_COUNT:
        raise ExecutionBoundaryError("resolution artifact requires six bindings")
    event_by_game: dict[str, str] = {}
    game_by_event: dict[str, str] = {}
    for binding, item in zip(bindings, manifest["items"], strict=True):
        if not isinstance(binding, Mapping) or set(binding) != BINDING_FIELDS:
            raise ExecutionBoundaryError("event binding schema is invalid")
        expected = {key: item[key] for key in (
            "sample_item_id", "canonical_game_id", "home_team", "away_team",
            "kickoff_at",
        )}
        if any(binding.get(key) != value for key, value in expected.items()):
            raise ExecutionBoundaryError("event binding is not game-bound")
        event_id = _identity(binding.get("provider_event_id"), "provider_event_id")
        game_id = item["canonical_game_id"]
        if event_by_game.setdefault(game_id, event_id) != event_id:
            raise ExecutionBoundaryError("one game has conflicting provider events")
        if game_by_event.setdefault(event_id, game_id) != game_id:
            raise ExecutionBoundaryError("one provider event crosses games")


def build_execution_authorization(
    manifest: Mapping[str, Any],
    resolution: Mapping[str, Any],
    execution_authorization_id: str,
) -> dict[str, Any]:
    validate_resolution_artifact(resolution, manifest)
    base = {
        "schema_version": 1,
        "authorization_version": AUTH_VERSION,
        "execution_authorization_id": _identity(
            execution_authorization_id, "execution_authorization_id", 128
        ),
        "manifest_sha256": manifest["manifest_sha256"],
        "resolution_artifact_sha256": resolution["artifact_sha256"],
        "sample_item_ids": [item["sample_item_id"] for item in manifest["items"]],
        "provider_event_bindings": [
            {key: binding[key] for key in ("sample_item_id", "provider_event_id")}
            for binding in resolution["bindings"]
        ],
        "maximum_acquisition_attempts": MAX_REQUEST_COUNT,
    }
    return {**base, "authorization_sha256": _digest(base)}


def validate_execution_authorization(
    authorization: Mapping[str, Any],
    manifest: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> None:
    if set(authorization) != AUTH_FIELDS:
        raise ExecutionBoundaryError("execution authorization schema is invalid")
    material = dict(authorization)
    claimed = material.pop("authorization_sha256", None)
    if claimed != _digest(material):
        raise ExecutionBoundaryError("execution authorization hash is invalid")
    expected = build_execution_authorization(
        manifest, resolution, authorization.get("execution_authorization_id")
    )
    if _canonical(authorization) != _canonical(expected):
        raise ExecutionBoundaryError("execution authorization is not authoritative")


@dataclass(frozen=True)
class PlayerTDRequest:
    sample_item_id: str
    provider_event_id: str
    canonical_game_id: str
    requested_snapshot_at: str
    market: str
    books: tuple[str, ...]
    region: str
    odds_format: str


@dataclass(frozen=True)
class TransportResult:
    succeeded: bool
    underlying_request_count: int
    retry_required: bool = False
    pagination_required: bool = False
    fallback_required: bool = False
    discovery_required: bool = False


@runtime_checkable
class SingleRequestTransport(Protocol):
    def send_once(self, request: PlayerTDRequest) -> TransportResult:
        """Exactly one request; no retry, discovery, pagination, or fallback."""
        ...


@dataclass(frozen=True)
class ExecutionStatus:
    state: str
    completed: tuple[str, ...]
    failed: tuple[str, ...]
    attempted_indeterminate: tuple[str, ...]
    untouched: tuple[str, ...]


def _append(path: Path, event: Mapping[str, Any]) -> None:
    with path.open("ab", buffering=0) as handle:
        handle.write((_canonical(event) + "\n").encode())
        os.fsync(handle.fileno())


def initialize_execution_ledger(path: Path | str, authorization: Mapping[str, Any]) -> None:
    ledger = Path(path)
    if ledger.is_symlink():
        raise ExecutionBoundaryError("ledger cannot be a symlink")
    ledger.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "state": "AUTHORIZED",
        "execution_authorization_id": authorization["execution_authorization_id"],
        "authorization_sha256": authorization["authorization_sha256"],
    }
    try:
        with ledger.open("xb", buffering=0) as handle:
            handle.write((_canonical(event) + "\n").encode())
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ExecutionBoundaryError("execution ledger already exists") from exc


def _events(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink():
        raise ExecutionBoundaryError("ledger cannot be a symlink")
    return [strict_json_loads(line) for line in path.read_text().splitlines()]


def read_execution_status(path: Path | str, item_ids: Sequence[str]) -> ExecutionStatus:
    events = _events(Path(path))
    attempted = [e["sample_item_id"] for e in events if e.get("state") == "ITEM_ATTEMPTED"]
    completed = [e["sample_item_id"] for e in events if e.get("state") == "ITEM_SUCCEEDED"]
    failed = [e["sample_item_id"] for e in events if e.get("state") == "ITEM_FAILED"]
    return ExecutionStatus(
        state=str(events[-1].get("state")),
        completed=tuple(completed),
        failed=tuple(failed),
        attempted_indeterminate=tuple(
            item for item in attempted if item not in completed and item not in failed
        ),
        untouched=tuple(item for item in item_ids if item not in attempted),
    )


__all__ = [
    "ExecutionBoundaryError", "ExecutionStatus", "PlayerTDRequest",
    "SingleRequestTransport", "TransportResult", "build_execution_authorization",
    "build_resolution_artifact", "initialize_execution_ledger",
    "load_strict_json", "read_execution_status", "strict_json_loads",
    "validate_execution_authorization", "validate_resolution_artifact",
]
