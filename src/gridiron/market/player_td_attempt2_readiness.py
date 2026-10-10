"""Pure zero-credit readiness gate for the authorized Player-ATTD attempt 2."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gridiron.market.player_td_execution import load_strict_json, strict_json_loads
from gridiron.market.player_td_second_attempt_authority import (
    BOOKMAKERS,
    DISCOVERY_LIMIT,
    MARKET_LIMIT,
    PREDECESSOR_CLAIM_SHA256,
    PREDECESSOR_EXECUTION_IDENTITY,
    PREDECESSOR_LEDGER_SHA256,
    PREDECESSOR_METADATA_SHA256,
    PREDECESSOR_RAW_RESPONSE_SHA256,
    PREDECESSOR_TERMINAL_RECORD_SHA256,
    PREDECESSOR_TERMINAL_STATE,
    PROHIBITED_EXPANSION,
    SECOND_ATTEMPT_EVENT_ROOT,
    SECOND_ATTEMPT_MARKET_ROOT,
    SECOND_ATTEMPT_ROOT,
    SECOND_ATTEMPT_STATE_ROOT,
    TOTAL_LIMIT,
    build_second_attempt_authority,
    validate_second_attempt_authority,
)

ATTEMPT_2_READY_FOR_EXECUTION = "ATTEMPT_2_READY_FOR_EXECUTION"
ATTEMPT_2_BLOCKED = "ATTEMPT_2_BLOCKED"

REFERENCE_ROOT = Path("data/reference/player_td_sample_v1")
AUTHORITY_PATH = REFERENCE_ROOT / "step93j5_second_attempt_authority.json"
MANIFEST_PATH = REFERENCE_ROOT / "step93c_player_td_sample_manifest.json"
ATTD_AUTHORITY_PATH = REFERENCE_ROOT / "step93j1_historical_authority.json"
EVENT_AUTHORITY_PATH = (
    REFERENCE_ROOT / "step93j1a_historical_event_resolution_authority.json"
)
J3_ROOT = Path("data/research/player_td_validation/step93c_sample")
J3_RESPONSE = Path("event_resolution/2023_01_det_kc.response.json")
J3_METADATA = Path("event_resolution/2023_01_det_kc.metadata.json")
J3_CLAIM = Path(
    "execution/e61e72001013bcd24a96ceb0e779cb6d4f7969901afc453bfbef6917120e1567.claimed"
)
J3_LEDGER = Path(
    "execution/e61e72001013bcd24a96ceb0e779cb6d4f7969901afc453bfbef6917120e1567.jsonl"
)
AUTHORITY_FILE_SHA256 = (
    "cb9f984238ec7f0b5410fc6f0f1af433bec986aa4cf268b1712ade15ce323ab6"
)
EXPECTED_AUTHORITY_SHA256 = (
    "234cb16eb002c4ecc1345b843b98d93fa87f86cb4abf5ea837396a8cfc6ccd0a"
)
EXPECTED_ATTEMPT2_IDENTITY = (
    "38182ab37f443dfedc12dc489c623d988e1a25f673bd5e4b877d2ebc013a13c1"
)
EXPECTED_STATES = (
    "AUTHORIZED",
    "STARTED",
    "DISCOVERY_ATTEMPTED",
    "FAILED_PARTIAL",
)


class Attempt2ReadinessError(ValueError):
    """A material attempt-2 readiness invariant failed."""


@dataclass(frozen=True)
class Attempt2ExecutionPlan:
    execution_identity: str
    discovery_requests: tuple[tuple[str, str], ...]
    market_requests: tuple[tuple[str, str, str, str, str, tuple[str, ...]], ...]
    discovery_limit: int
    market_limit: int
    total_limit: int
    state_root: str
    event_evidence_root: str
    market_evidence_root: str
    prohibited_expansion: tuple[str, ...]


@dataclass(frozen=True)
class Attempt2ReadinessResult:
    status: str
    failures: tuple[str, ...]
    plan: Attempt2ExecutionPlan | None


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


def _require_regular_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise Attempt2ReadinessError("required governed file is missing or unsafe")
    return path.read_bytes()


def _load_authority(root: Path) -> dict[str, Any]:
    path = root / AUTHORITY_PATH
    raw = _require_regular_file(path)
    if hashlib.sha256(raw).hexdigest() != AUTHORITY_FILE_SHA256:
        raise Attempt2ReadinessError("J.5 artifact hash is invalid")
    authority = load_strict_json(path)
    validate_second_attempt_authority(authority)
    if authority.get("authority_sha256") != EXPECTED_AUTHORITY_SHA256:
        raise Attempt2ReadinessError("J.5 authority identity is invalid")
    if authority.get("second_attempt_execution_identity") != EXPECTED_ATTEMPT2_IDENTITY:
        raise Attempt2ReadinessError("attempt-2 execution identity is invalid")
    return authority


def _inventory(root: Path) -> set[Path]:
    governed = root / J3_ROOT
    if governed.is_symlink() or not governed.is_dir():
        raise Attempt2ReadinessError("J.3 evidence root is missing or unsafe")
    observed: set[Path] = set()
    for path in governed.rglob("*"):
        relative = path.relative_to(governed)
        if relative.parts and relative.parts[0] == "attempt2":
            continue
        if path.is_symlink():
            raise Attempt2ReadinessError("J.3 evidence contains a symlink")
        if path.is_file():
            observed.add(relative)
    return observed


def _validate_ledger(raw: bytes) -> None:
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise Attempt2ReadinessError("J.3 ledger encoding is invalid") from exc
    records = [strict_json_loads(line) for line in lines]
    if tuple(record.get("state") for record in records) != EXPECTED_STATES:
        raise Attempt2ReadinessError("J.3 ledger states are invalid")
    previous = "0" * 64
    for sequence, record in enumerate(records):
        material = dict(record)
        claimed = material.pop("record_sha256", None)
        if (
            record.get("sequence") != sequence
            or record.get("previous_record_sha256") != previous
            or record.get("execution_identity") != PREDECESSOR_EXECUTION_IDENTITY
            or claimed != _digest(material)
        ):
            raise Attempt2ReadinessError("J.3 ledger chain is invalid")
        previous = str(claimed)
    if previous != PREDECESSOR_TERMINAL_RECORD_SHA256:
        raise Attempt2ReadinessError("J.3 terminal record is invalid")


def _verify_predecessor(root: Path) -> None:
    permitted = {J3_RESPONSE, J3_METADATA, J3_CLAIM, J3_LEDGER}
    if _inventory(root) != permitted:
        raise Attempt2ReadinessError("J.3 evidence inventory is invalid")
    expected_hashes = {
        J3_RESPONSE: PREDECESSOR_RAW_RESPONSE_SHA256,
        J3_METADATA: PREDECESSOR_METADATA_SHA256,
        J3_CLAIM: PREDECESSOR_CLAIM_SHA256,
        J3_LEDGER: PREDECESSOR_LEDGER_SHA256,
    }
    payloads: dict[Path, bytes] = {}
    for relative, expected in expected_hashes.items():
        raw = _require_regular_file(root / J3_ROOT / relative)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise Attempt2ReadinessError("J.3 retained evidence hash is invalid")
        payloads[relative] = raw
    if payloads[J3_CLAIM].decode("ascii") != PREDECESSOR_EXECUTION_IDENTITY:
        raise Attempt2ReadinessError("J.3 claim identity is invalid")
    _validate_ledger(payloads[J3_LEDGER])
    metadata = strict_json_loads(payloads[J3_METADATA].decode("utf-8"))
    if (
        metadata.get("raw_sha256") != PREDECESSOR_RAW_RESPONSE_SHA256
        or metadata.get("byte_count") != len(payloads[J3_RESPONSE])
        or metadata.get("http_status") != 401
    ):
        raise Attempt2ReadinessError("J.3 metadata binding is invalid")


def _verify_empty_attempt2_namespace(root: Path) -> None:
    path = root / SECOND_ATTEMPT_ROOT
    if path.exists() or path.is_symlink():
        raise Attempt2ReadinessError("attempt-2 namespace is not pristine")


def _build_plan(
    authority: dict[str, Any],
    manifest: dict[str, Any],
    event_authority: dict[str, Any],
) -> Attempt2ExecutionPlan:
    discovery = tuple(
        (item["canonical_game_id"], item["discovery_date"])
        for item in authority["discovery_plan"]
    )
    expected_discovery = tuple(
        (item["canonical_game_id"], item["discovery_date"])
        for item in event_authority["games"]
    )
    market = tuple(
        (
            item["canonical_game_id"],
            item["snapshot_label"],
            item["requested_snapshot_at"],
            item["market"],
            item["region"],
            tuple(item["bookmakers"]),
        )
        for item in authority["market_plan"]
    )
    expected_market = tuple(
        (
            item["canonical_game_id"],
            item["snapshot_label"],
            item["requested_snapshot_at"],
            item["market"],
            item["region"],
            tuple(item["books"]),
        )
        for item in manifest["items"]
    )
    if discovery != expected_discovery or market != expected_market:
        raise Attempt2ReadinessError("attempt-2 execution plan is not frozen")
    if any(item[5] != BOOKMAKERS for item in market):
        raise Attempt2ReadinessError("attempt-2 bookmaker scope is invalid")
    if (
        authority["maximum_discovery_operations"] != DISCOVERY_LIMIT
        or authority["maximum_market_operations"] != MARKET_LIMIT
        or authority["maximum_combined_provider_operations"] != TOTAL_LIMIT
        or len(discovery) != DISCOVERY_LIMIT
        or len(market) != MARKET_LIMIT
    ):
        raise Attempt2ReadinessError("attempt-2 request budget is invalid")
    if tuple(authority["prohibited_expansion"]) != PROHIBITED_EXPANSION:
        raise Attempt2ReadinessError("attempt-2 expansion prohibitions are invalid")
    if (
        authority["execution_enabled"] is not False
        or authority["execution_precondition"]
        != "HUMAN_CONFIRMED_PAID_HISTORICAL_ACCESS"
        or authority["historical_content_availability"]
        != "UNVERIFIED_UNTIL_ACQUISITION"
        or authority["incomplete_evidence_behavior"] != "PRESERVE_AND_FAIL_CLOSED"
    ):
        raise Attempt2ReadinessError("attempt-2 authorization semantics are invalid")
    expected_roots = (
        SECOND_ATTEMPT_STATE_ROOT.as_posix(),
        SECOND_ATTEMPT_EVENT_ROOT.as_posix(),
        SECOND_ATTEMPT_MARKET_ROOT.as_posix(),
    )
    actual_roots = (
        authority["state_root"],
        authority["event_evidence_root"],
        authority["market_evidence_root"],
    )
    if actual_roots != expected_roots:
        raise Attempt2ReadinessError("attempt-2 evidence namespace is invalid")
    return Attempt2ExecutionPlan(
        execution_identity=authority["second_attempt_execution_identity"],
        discovery_requests=discovery,
        market_requests=market,
        discovery_limit=DISCOVERY_LIMIT,
        market_limit=MARKET_LIMIT,
        total_limit=TOTAL_LIMIT,
        state_root=actual_roots[0],
        event_evidence_root=actual_roots[1],
        market_evidence_root=actual_roots[2],
        prohibited_expansion=PROHIBITED_EXPANSION,
    )


def evaluate_attempt2_readiness(
    *, repository_root: Path | str = Path(".")
) -> Attempt2ReadinessResult:
    """Evaluate all attempt-2 gates without credentials, network, or writes."""
    root = Path(repository_root)
    try:
        authority = _load_authority(root)
        _verify_predecessor(root)
        _verify_empty_attempt2_namespace(root)
        manifest = load_strict_json(root / MANIFEST_PATH)
        attd_authority = load_strict_json(root / ATTD_AUTHORITY_PATH)
        event_authority = load_strict_json(root / EVENT_AUTHORITY_PATH)
        predecessor = {
            "execution_identity": PREDECESSOR_EXECUTION_IDENTITY,
            "terminal_state": PREDECESSOR_TERMINAL_STATE,
            "terminal_record_sha256": PREDECESSOR_TERMINAL_RECORD_SHA256,
            "ledger_sha256": PREDECESSOR_LEDGER_SHA256,
            "claim_sha256": PREDECESSOR_CLAIM_SHA256,
            "raw_response_sha256": PREDECESSOR_RAW_RESPONSE_SHA256,
            "metadata_sha256": PREDECESSOR_METADATA_SHA256,
            "failure_classification": authority["predecessor_failure_classification"],
            "provider_result": authority["predecessor_provider_result"],
        }
        rebuilt = build_second_attempt_authority(
            manifest, attd_authority, event_authority, predecessor
        )
        if rebuilt != authority:
            raise Attempt2ReadinessError("J.5 authority cannot be reproduced")
        plan = _build_plan(authority, manifest, event_authority)
    except Exception as exc:  # noqa: BLE001 - every material uncertainty blocks
        return Attempt2ReadinessResult(
            status=ATTEMPT_2_BLOCKED,
            failures=(type(exc).__name__,),
            plan=None,
        )
    return Attempt2ReadinessResult(
        status=ATTEMPT_2_READY_FOR_EXECUTION,
        failures=(),
        plan=plan,
    )


__all__ = [
    "ATTEMPT_2_BLOCKED",
    "ATTEMPT_2_READY_FOR_EXECUTION",
    "Attempt2ExecutionPlan",
    "Attempt2ReadinessResult",
    "evaluate_attempt2_readiness",
]
