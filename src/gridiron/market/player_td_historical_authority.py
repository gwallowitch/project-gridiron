"""Frozen, disabled authority contract for the Step 93C historical ATTD sample.

This module defines research scope only. Project Gridiron has no active
historical Player ATTD transport path in Step 93J.1. A future Step 93J.2 must
explicitly pin the independently reviewed artifact hash and add a separately
reviewed execution integration before any provider call is possible.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NamedTuple

from gridiron.market.player_td_execution import ExecutionBoundaryError
from gridiron.market.player_td_sample import (
    BOOKS,
    MAX_REQUEST_COUNT,
    ODDS_FORMAT,
    PURPOSE,
    REGION,
    validate_frozen_sample_manifest,
)

AUTHORITY_SCHEMA_VERSION = 1
AUTHORITY_VERSION = "step93j1-historical-player-attd-validation-v1"
AUTHORITY_TYPE = "HISTORICAL_PLAYER_ATTD_VALIDATION_SAMPLE_V1"
CLASSIFICATION = "HISTORICAL_NON_PRODUCTION_INPUT_VALIDATION"
FROZEN_MANIFEST_SHA256 = (
    "b120ac96101f01846906a66eab1987cfa57dbfbbd742e58384fb1f5f4edda927"
)
MARKET = "player_anytime_td"
RAW_ARTIFACT_ROOT = Path("data/research/player_td_validation/step93c_sample/raw")
RAW_METADATA_FIELDS = frozenset({
    "schema_version", "authority_type", "authority_sha256", "manifest_sha256",
    "sample_item_id", "provider_event_id", "requested_snapshot_at",
    "acquired_at", "http_status", "request_scope", "raw_artifact_sha256",
    "raw_byte_count", "response_file",
})
AUTHORITY_FIELDS = frozenset({
    "schema_version", "authority_version", "authority_type",
    "manifest_sha256", "item_count", "maximum_request_count", "market",
    "region", "odds_format", "bookmakers", "purpose", "classification",
    "raw_artifact_root", "execution_enabled", "authority_sha256",
})


class HistoricalAuthorityError(ValueError):
    pass


class HistoricalRawDestination(NamedTuple):
    response_path: Path
    metadata_path: Path


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def build_historical_authority(
    manifest: Mapping[str, Any],
    schedule: object,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the deterministic, non-activating authority-scope artifact."""
    validate_frozen_sample_manifest(manifest, schedule, provenance)
    items = manifest["items"]
    if manifest["manifest_sha256"] != FROZEN_MANIFEST_SHA256:
        raise HistoricalAuthorityError("manifest is not the frozen Step 93C artifact")
    base = {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "authority_version": AUTHORITY_VERSION,
        "authority_type": AUTHORITY_TYPE,
        "manifest_sha256": FROZEN_MANIFEST_SHA256,
        "item_count": len(items),
        "maximum_request_count": manifest["maximum_request_count"],
        "market": MARKET,
        "region": REGION,
        "odds_format": ODDS_FORMAT,
        "bookmakers": list(BOOKS),
        "purpose": PURPOSE,
        "classification": CLASSIFICATION,
        "raw_artifact_root": RAW_ARTIFACT_ROOT.as_posix(),
        "execution_enabled": False,
    }
    return {**base, "authority_sha256": _digest(base)}


def validate_historical_authority(artifact: Mapping[str, Any]) -> None:
    """Validate exact Step 93J.1 scope; validation never activates execution."""
    if set(artifact) != AUTHORITY_FIELDS:
        raise HistoricalAuthorityError("historical authority schema is invalid")
    expected = {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "authority_version": AUTHORITY_VERSION,
        "authority_type": AUTHORITY_TYPE,
        "manifest_sha256": FROZEN_MANIFEST_SHA256,
        "item_count": MAX_REQUEST_COUNT,
        "maximum_request_count": MAX_REQUEST_COUNT,
        "market": MARKET,
        "region": REGION,
        "odds_format": ODDS_FORMAT,
        "bookmakers": list(BOOKS),
        "purpose": PURPOSE,
        "classification": CLASSIFICATION,
        "raw_artifact_root": RAW_ARTIFACT_ROOT.as_posix(),
        "execution_enabled": False,
    }
    if any(artifact.get(key) != value for key, value in expected.items()):
        raise HistoricalAuthorityError("historical authority scope is invalid")
    material = dict(artifact)
    claimed = material.pop("authority_sha256", None)
    if claimed != _digest(material):
        raise HistoricalAuthorityError("historical authority SHA-256 is invalid")


def historical_raw_destination(
    artifact: Mapping[str, Any], sample_item_id: str
) -> HistoricalRawDestination:
    """Return deterministic future paths; this function performs no writes."""
    validate_historical_authority(artifact)
    if (
        not isinstance(sample_item_id, str)
        or len(sample_item_id) != 64
        or any(character not in "0123456789abcdef" for character in sample_item_id)
    ):
        raise HistoricalAuthorityError("sample item identity is invalid")
    root = RAW_ARTIFACT_ROOT / str(artifact["authority_sha256"])
    return HistoricalRawDestination(
        root / f"{sample_item_id}.response.json",
        root / f"{sample_item_id}.metadata.json",
    )


def historical_execution_identity(artifact: Mapping[str, Any]) -> str:
    """Bind any future one-shot state namespace to authority and manifest."""
    validate_historical_authority(artifact)
    return _digest({
        "authority_sha256": artifact["authority_sha256"],
        "manifest_sha256": artifact["manifest_sha256"],
    })


def execute_historical_validation_sample_once(*args: object, **kwargs: object) -> None:
    """Fail closed in Step 93J.1 pending an independently reviewed hash pin."""
    del args, kwargs
    raise ExecutionBoundaryError(
        "historical Player ATTD acquisition is disabled pending Step 93J.2 review"
    )


__all__ = [
    "AUTHORITY_TYPE",
    "FROZEN_MANIFEST_SHA256",
    "RAW_METADATA_FIELDS",
    "HistoricalAuthorityError",
    "HistoricalRawDestination",
    "build_historical_authority",
    "execute_historical_validation_sample_once",
    "historical_execution_identity",
    "historical_raw_destination",
    "validate_historical_authority",
]
