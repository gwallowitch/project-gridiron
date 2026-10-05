"""Disabled authority for a second bounded historical Player-ATTD attempt.

This module is declarative and offline. It cannot read credentials, contact a
provider, or execute either the consumed first attempt or the future second
attempt.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from gridiron.market.player_td_event_resolution_authority import (
    validate_event_resolution_authority,
)
from gridiron.market.player_td_historical_authority import (
    validate_historical_authority,
)

AUTHORITY_SCHEMA_VERSION = 1
AUTHORITY_VERSION = "step93j5-second-attempt-authority-v1"
AUTHORITY_TYPE = "HISTORICAL_PLAYER_ATTD_SECOND_ATTEMPT_AUTHORITY_V1"
CLASSIFICATION = "HISTORICAL_NON_PRODUCTION_INPUT_VALIDATION_SECOND_ATTEMPT"
EXECUTION_PRECONDITION = "HUMAN_CONFIRMED_PAID_HISTORICAL_ACCESS"
CONTENT_AVAILABILITY = "UNVERIFIED_UNTIL_ACQUISITION"

MANIFEST_SHA256 = "b120ac96101f01846906a66eab1987cfa57dbfbbd742e58384fb1f5f4edda927"
ATTD_AUTHORITY_SHA256 = (
    "4f7f3baab797051909c284f30102254e5d9f2f255e30ffb24c077bf984c2dd77"
)
EVENT_AUTHORITY_SHA256 = (
    "d8136aab1a1915ca99cc1b6cb5bf8bff113ae06fd32c67238423305beebfc980"
)
J2_FREEZE_COMMIT = "9fe087d53ac104a77feaef3f5dd15a5dcdd8af7f"
PREDECESSOR_EXECUTION_IDENTITY = (
    "e61e72001013bcd24a96ceb0e779cb6d4f7969901afc453bfbef6917120e1567"
)
PREDECESSOR_TERMINAL_STATE = "FAILED_PARTIAL"
PREDECESSOR_FAILURE_CLASSIFICATION = (
    "AUTHORIZED_ACQUISITION_ATTEMPT_FAILED_PROVIDER_ACCESS"
)
PREDECESSOR_PROVIDER_RESULT = "HISTORICAL_UNAVAILABLE_ON_FREE_USAGE_PLAN"
PREDECESSOR_TERMINAL_RECORD_SHA256 = (
    "16b72518ca44a7f6d27aa75cbd49aca4e98e2536623850d2417aae2a36a458da"
)
PREDECESSOR_LEDGER_SHA256 = (
    "c8d02406ff58c180142c0b48439dca4c777661fd1d297b357549946317806319"
)
PREDECESSOR_CLAIM_SHA256 = (
    "01240821c7bbdbb6f5446c6a72d3b8647c910a90745d921afb1d75dd2a4b0dd8"
)
PREDECESSOR_RAW_RESPONSE_SHA256 = (
    "baaa10cb5138c0c4a4cc33387b61c6b01708e314faa2c6d42ed27250fa9f4215"
)
PREDECESSOR_METADATA_SHA256 = (
    "634da7895c254dda77352314b275969b515c4ff1efa8b4d791b4321482ebc5fe"
)

DISCOVERY_LIMIT = 3
MARKET_LIMIT = 6
TOTAL_LIMIT = 9
SECOND_ATTEMPT_ROOT = Path(
    "data/research/player_td_validation/step93c_sample/attempt2"
)
SECOND_ATTEMPT_STATE_ROOT = SECOND_ATTEMPT_ROOT / "execution"
SECOND_ATTEMPT_EVENT_ROOT = SECOND_ATTEMPT_ROOT / "event_resolution"
SECOND_ATTEMPT_MARKET_ROOT = SECOND_ATTEMPT_ROOT / "raw"

BOOKMAKERS = ("draftkings", "fanduel", "betmgm")
DISCOVERY_PLAN = (
    ("2023_01_DET_KC", "2023-09-07T12:20:00Z"),
    ("2024_01_BAL_KC", "2024-09-05T12:20:00Z"),
    ("2025_01_DAL_PHI", "2025-09-04T12:20:00Z"),
)
MARKET_PLAN = (
    ("2023_01_DET_KC", "T12H", "2023-09-07T12:20:00Z"),
    ("2023_01_DET_KC", "T1H", "2023-09-07T23:20:00Z"),
    ("2024_01_BAL_KC", "T12H", "2024-09-05T12:20:00Z"),
    ("2024_01_BAL_KC", "T1H", "2024-09-05T23:20:00Z"),
    ("2025_01_DAL_PHI", "T12H", "2025-09-04T12:20:00Z"),
    ("2025_01_DAL_PHI", "T1H", "2025-09-04T23:20:00Z"),
)
PROHIBITED_EXPANSION = (
    "retry",
    "resend",
    "pagination",
    "fallback",
    "balance_request",
    "alternate_timestamp",
    "alternate_game",
    "alternate_event",
    "alternate_bookmaker",
    "budget_borrowing",
    "manual_event_id_substitution",
)


class SecondAttemptAuthorityError(ValueError):
    """The Step 93J.5 authority or one of its bindings is invalid."""


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _expected_discovery_plan() -> list[dict[str, str]]:
    return [
        {"canonical_game_id": game_id, "discovery_date": discovery_date}
        for game_id, discovery_date in DISCOVERY_PLAN
    ]


def _expected_market_plan() -> list[dict[str, Any]]:
    return [
        {
            "canonical_game_id": game_id,
            "snapshot_label": label,
            "requested_snapshot_at": requested_at,
            "market": "player_anytime_td",
            "region": "us",
            "odds_format": "american",
            "bookmakers": list(BOOKMAKERS),
        }
        for game_id, label, requested_at in MARKET_PLAN
    ]


def _base_authority() -> dict[str, Any]:
    return {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "authority_version": AUTHORITY_VERSION,
        "authority_type": AUTHORITY_TYPE,
        "classification": CLASSIFICATION,
        "manifest_sha256": MANIFEST_SHA256,
        "attd_authority_sha256": ATTD_AUTHORITY_SHA256,
        "event_authority_sha256": EVENT_AUTHORITY_SHA256,
        "j2_freeze_commit": J2_FREEZE_COMMIT,
        "attempt_number": 2,
        "predecessor_execution_identity": PREDECESSOR_EXECUTION_IDENTITY,
        "predecessor_terminal_state": PREDECESSOR_TERMINAL_STATE,
        "predecessor_failure_classification": (
            PREDECESSOR_FAILURE_CLASSIFICATION
        ),
        "predecessor_provider_result": PREDECESSOR_PROVIDER_RESULT,
        "predecessor_terminal_record_sha256": (
            PREDECESSOR_TERMINAL_RECORD_SHA256
        ),
        "predecessor_ledger_sha256": PREDECESSOR_LEDGER_SHA256,
        "predecessor_claim_sha256": PREDECESSOR_CLAIM_SHA256,
        "predecessor_raw_response_sha256": PREDECESSOR_RAW_RESPONSE_SHA256,
        "predecessor_metadata_sha256": PREDECESSOR_METADATA_SHA256,
        "discovery_plan": _expected_discovery_plan(),
        "market_plan": _expected_market_plan(),
        "maximum_discovery_operations": DISCOVERY_LIMIT,
        "maximum_market_operations": MARKET_LIMIT,
        "maximum_combined_provider_operations": TOTAL_LIMIT,
        "prohibited_expansion": list(PROHIBITED_EXPANSION),
        "execution_precondition": EXECUTION_PRECONDITION,
        "paid_access_confirmation_source": "EXTERNAL_HUMAN_DECISION",
        "historical_content_availability": CONTENT_AVAILABILITY,
        "incomplete_evidence_behavior": "PRESERVE_AND_FAIL_CLOSED",
        "second_attempt_root": SECOND_ATTEMPT_ROOT.as_posix(),
        "state_root": SECOND_ATTEMPT_STATE_ROOT.as_posix(),
        "event_evidence_root": SECOND_ATTEMPT_EVENT_ROOT.as_posix(),
        "market_evidence_root": SECOND_ATTEMPT_MARKET_ROOT.as_posix(),
        "execution_enabled": False,
    }


def _expected_authority() -> dict[str, Any]:
    base = _base_authority()
    authority_sha256 = _digest(base)
    execution_identity = _digest({
        "attempt_number": 2,
        "authority_sha256": authority_sha256,
        "predecessor_execution_identity": PREDECESSOR_EXECUTION_IDENTITY,
    })
    return {
        **base,
        "authority_sha256": authority_sha256,
        "second_attempt_execution_identity": execution_identity,
    }


def _validate_manifest(manifest: Mapping[str, Any]) -> None:
    material = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if (
        manifest.get("manifest_sha256") != MANIFEST_SHA256
        or _digest(material) != MANIFEST_SHA256
    ):
        raise SecondAttemptAuthorityError("manifest binding is invalid")
    items = manifest.get("items")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise SecondAttemptAuthorityError("manifest items are invalid")
    observed = [
        (
            item.get("canonical_game_id"),
            item.get("snapshot_label"),
            item.get("requested_snapshot_at"),
            item.get("market"),
            item.get("region"),
            item.get("odds_format"),
            tuple(item.get("books", ())),
        )
        for item in items
        if isinstance(item, Mapping)
    ]
    expected = [
        (game_id, label, requested_at, "player_anytime_td", "us", "american", BOOKMAKERS)
        for game_id, label, requested_at in MARKET_PLAN
    ]
    if observed != expected:
        raise SecondAttemptAuthorityError("frozen market plan is invalid")


def build_second_attempt_authority(
    manifest: Mapping[str, Any],
    attd_authority: Mapping[str, Any],
    event_authority: Mapping[str, Any],
    predecessor_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the deterministic disabled authority from exact frozen bindings."""
    _validate_manifest(manifest)
    validate_historical_authority(attd_authority)
    validate_event_resolution_authority(event_authority)
    if attd_authority.get("authority_sha256") != ATTD_AUTHORITY_SHA256:
        raise SecondAttemptAuthorityError("J.1 authority binding is invalid")
    if event_authority.get("authority_sha256") != EVENT_AUTHORITY_SHA256:
        raise SecondAttemptAuthorityError("J.1A authority binding is invalid")
    expected_binding = {
        "execution_identity": PREDECESSOR_EXECUTION_IDENTITY,
        "terminal_state": PREDECESSOR_TERMINAL_STATE,
        "terminal_record_sha256": PREDECESSOR_TERMINAL_RECORD_SHA256,
        "ledger_sha256": PREDECESSOR_LEDGER_SHA256,
        "claim_sha256": PREDECESSOR_CLAIM_SHA256,
        "raw_response_sha256": PREDECESSOR_RAW_RESPONSE_SHA256,
        "metadata_sha256": PREDECESSOR_METADATA_SHA256,
        "failure_classification": PREDECESSOR_FAILURE_CLASSIFICATION,
        "provider_result": PREDECESSOR_PROVIDER_RESULT,
    }
    if dict(predecessor_binding) != expected_binding:
        raise SecondAttemptAuthorityError("predecessor evidence binding is invalid")
    return _expected_authority()


def validate_second_attempt_authority(artifact: Mapping[str, Any]) -> None:
    """Fail closed unless every Step 93J.5 field matches the frozen authority."""
    expected = _expected_authority()
    if dict(artifact) != expected:
        raise SecondAttemptAuthorityError("second-attempt authority is invalid")
    if artifact["second_attempt_execution_identity"] == PREDECESSOR_EXECUTION_IDENTITY:
        raise SecondAttemptAuthorityError("predecessor execution identity was reused")
    roots = {
        artifact["second_attempt_root"],
        artifact["state_root"],
        artifact["event_evidence_root"],
        artifact["market_evidence_root"],
    }
    if any("attempt2" not in root for root in roots):
        raise SecondAttemptAuthorityError("second-attempt path is not isolated")


__all__ = [
    "SecondAttemptAuthorityError",
    "build_second_attempt_authority",
    "validate_second_attempt_authority",
]
