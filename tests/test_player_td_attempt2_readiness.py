from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

import gridiron.market.player_td_attempt2_readiness as readiness
from gridiron.market.player_td_attempt2_readiness import (
    ATTEMPT_2_BLOCKED,
    ATTEMPT_2_READY_FOR_EXECUTION,
    evaluate_attempt2_readiness,
)

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data/reference/player_td_sample_v1"
EXECUTION_ID = "e61e72001013bcd24a96ceb0e779cb6d4f7969901afc453bfbef6917120e1567"
MANIFEST_SHA = "b120ac96101f01846906a66eab1987cfa57dbfbbd742e58384fb1f5f4edda927"
ATTD_SHA = "4f7f3baab797051909c284f30102254e5d9f2f255e30ffb24c077bf984c2dd77"
EVENT_SHA = "d8136aab1a1915ca99cc1b6cb5bf8bff113ae06fd32c67238423305beebfc980"


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _record(previous: dict[str, object] | None, state: str, **details: object):
    base = {
        "sequence": 0 if previous is None else int(previous["sequence"]) + 1,
        "previous_record_sha256": "0" * 64 if previous is None else previous["record_sha256"],
        "execution_identity": EXECUTION_ID,
        "manifest_sha256": MANIFEST_SHA,
        "attd_authority_sha256": ATTD_SHA,
        "event_authority_sha256": EVENT_SHA,
        "state": state,
        **details,
    }
    return {
        **base,
        "record_sha256": hashlib.sha256(_canonical(base).encode()).hexdigest(),
    }


def _write_j3_evidence(root: Path) -> None:
    governed = root / readiness.J3_ROOT
    response = (
        b'{"message":"Historical odds are only available on paid usage plans. '
        b'See usage plans at https://the-odds-api.com","error_code":"HISTORICAL_'
        b'UNAVAILABLE_ON_FREE_USAGE_PLAN","details_url":"https://the-odds-api.com/'
        b'liveapi/guides/v4/api-error-codes.html#historical-unavailable-on-free-usage-plan"}\n'
    )
    metadata = {
        "schema_version": 1,
        "event_authority_sha256": EVENT_SHA,
        "attd_authority_sha256": ATTD_SHA,
        "manifest_sha256": MANIFEST_SHA,
        "canonical_game_id": "2023_01_DET_KC",
        "discovery_date": "2023-09-07T12:20:00Z",
        "acquired_at": "2026-10-01T23:33:42.716001Z",
        "http_status": 401,
        "sport": "americanfootball_nfl",
        "endpoint_class": "HISTORICAL_EVENTS",
        "raw_sha256": hashlib.sha256(response).hexdigest(),
        "byte_count": len(response),
        "response_filename": "2023_01_det_kc.response.json",
    }
    records: list[dict[str, object]] = []
    records.append(_record(None, "AUTHORIZED"))
    records.append(_record(records[-1], "STARTED"))
    records.append(
        _record(
            records[-1],
            "DISCOVERY_ATTEMPTED",
            phase_attempt=1,
            item_id="2023_01_DET_KC",
        )
    )
    records.append(_record(records[-1], "FAILED_PARTIAL"))
    files = {
        readiness.J3_RESPONSE: response,
        readiness.J3_METADATA: (_canonical(metadata) + "\n").encode(),
        readiness.J3_CLAIM: EXECUTION_ID.encode(),
        readiness.J3_LEDGER: (
            "".join(_canonical(record) + "\n" for record in records)
        ).encode(),
    }
    for relative, content in files.items():
        path = governed / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    assert records[-1]["record_sha256"] == readiness.PREDECESSOR_TERMINAL_RECORD_SHA256
    assert hashlib.sha256(files[readiness.J3_RESPONSE]).hexdigest() == (
        readiness.PREDECESSOR_RAW_RESPONSE_SHA256
    )
    assert hashlib.sha256(files[readiness.J3_METADATA]).hexdigest() == (
        readiness.PREDECESSOR_METADATA_SHA256
    )
    assert hashlib.sha256(files[readiness.J3_CLAIM]).hexdigest() == (
        readiness.PREDECESSOR_CLAIM_SHA256
    )
    assert hashlib.sha256(files[readiness.J3_LEDGER]).hexdigest() == (
        readiness.PREDECESSOR_LEDGER_SHA256
    )


@pytest.fixture
def ready_root(tmp_path: Path) -> Path:
    shutil.copytree(REFERENCE, tmp_path / readiness.REFERENCE_ROOT)
    _write_j3_evidence(tmp_path)
    return tmp_path


def _assert_blocked(root: Path) -> None:
    result = evaluate_attempt2_readiness(repository_root=root)
    assert result.status == ATTEMPT_2_BLOCKED
    assert result.plan is None
    assert result.failures


def _mutate_authority(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    path = root / readiness.AUTHORITY_PATH
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact[field] = value
    raw = (_canonical(artifact) + "\n").encode()
    path.write_bytes(raw)
    monkeypatch.setattr(readiness, "AUTHORITY_FILE_SHA256", hashlib.sha256(raw).hexdigest())


def test_canonical_state_is_ready(ready_root: Path) -> None:
    result = evaluate_attempt2_readiness(repository_root=ready_root)
    assert result.status == ATTEMPT_2_READY_FOR_EXECUTION
    assert result.failures == ()
    assert result.plan is not None
    assert len(result.plan.discovery_requests) == 3
    assert len(result.plan.market_requests) == 6
    assert result.plan.total_limit == 9


def test_wrong_authority_file_hash_blocks(ready_root: Path) -> None:
    path = ready_root / readiness.AUTHORITY_PATH
    path.write_bytes(path.read_bytes() + b" ")
    _assert_blocked(ready_root)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("authority_sha256", "0" * 64),
        ("second_attempt_execution_identity", "0" * 64),
        ("predecessor_execution_identity", "0" * 64),
        ("predecessor_terminal_state", "COMPLETED"),
        ("maximum_discovery_operations", 4),
        ("maximum_market_operations", 7),
        ("maximum_combined_provider_operations", 10),
        ("prohibited_expansion", []),
        ("execution_enabled", True),
    ],
)
def test_authority_mutations_block(
    ready_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    _mutate_authority(ready_root, monkeypatch, field, value)
    _assert_blocked(ready_root)


def test_execution_plan_mutation_blocks(
    ready_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = ready_root / readiness.AUTHORITY_PATH
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["market_plan"][0]["bookmakers"] = ["alternate_provider"]
    raw = (_canonical(artifact) + "\n").encode()
    path.write_bytes(raw)
    monkeypatch.setattr(readiness, "AUTHORITY_FILE_SHA256", hashlib.sha256(raw).hexdigest())
    _assert_blocked(ready_root)


@pytest.mark.parametrize(
    "relative",
    [
        readiness.J3_RESPONSE,
        readiness.J3_METADATA,
        readiness.J3_CLAIM,
        readiness.J3_LEDGER,
    ],
)
def test_mutated_predecessor_evidence_blocks(ready_root: Path, relative: Path) -> None:
    path = ready_root / readiness.J3_ROOT / relative
    path.write_bytes(path.read_bytes() + b"mutated")
    _assert_blocked(ready_root)


@pytest.mark.parametrize(
    "relative",
    [
        Path("event_resolution/unexpected.json"),
        Path("raw/unexpected.response.json"),
    ],
)
def test_unexpected_first_attempt_evidence_blocks(
    ready_root: Path, relative: Path
) -> None:
    path = ready_root / readiness.J3_ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    _assert_blocked(ready_root)


@pytest.mark.parametrize(
    "relative",
    [
        Path("unexpected.json"),
        Path("execution/conflicting.claimed"),
    ],
)
def test_contaminated_attempt2_namespace_blocks(
    ready_root: Path, relative: Path
) -> None:
    path = ready_root / readiness.SECOND_ATTEMPT_ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("conflict", encoding="utf-8")
    _assert_blocked(ready_root)


def test_sample_mutation_blocks(ready_root: Path) -> None:
    path = ready_root / readiness.MANIFEST_PATH
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["items"][0]["canonical_game_id"] = "OTHER_GAME"
    path.write_text(_canonical(manifest) + "\n", encoding="utf-8")
    _assert_blocked(ready_root)


def test_readiness_is_credential_network_and_write_inert(
    ready_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("forbidden readiness side effect")

    before = {
        path.relative_to(ready_root): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in ready_root.rglob("*")
        if path.is_file()
    }
    monkeypatch.setattr("os.environ.get", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("urllib.request.build_opener", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    result = evaluate_attempt2_readiness(repository_root=ready_root)
    after = {
        path.relative_to(ready_root): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in ready_root.rglob("*")
        if path.is_file()
    }
    assert result.status == ATTEMPT_2_READY_FOR_EXECUTION
    assert after == before
