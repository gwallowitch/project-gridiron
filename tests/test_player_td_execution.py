from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import pytest

import gridiron.market.player_td_authorized_execution as secure_execution
from gridiron.market.player_td_execution import (
    ExecutionBoundaryError,
    TransportResult,
    build_execution_authorization,
    build_resolution_artifact,
    strict_json_loads,
    validate_execution_authorization,
    validate_resolution_artifact,
)

ROOT = Path("data/reference/player_td_sample_v1")


def authority():
    schedule = json.loads((ROOT / "player_td_schedule_2023_2025_v1.json").read_text())
    manifest = json.loads((ROOT / "step93c_player_td_sample_manifest.json").read_text())
    provenance = json.loads((ROOT / "schedule_provenance.json").read_text())
    event_ids = tuple(f"event-{index // 2}" for index in range(6))
    resolution = build_resolution_artifact(
        manifest, event_ids, resolution_method="offline-test",
        resolution_source="fixture", approved_by="test-reviewer",
    )
    authorization = build_execution_authorization(manifest, resolution, "test-auth-1")
    return schedule, manifest, provenance, resolution, authorization


class FakeTransport:
    def __init__(self, results=None, crash_at=None):
        self.results = list(results or [TransportResult(True, 1)] * 6)
        self.crash_at = crash_at
        self.calls = []

    def send_once(self, request):
        self.calls.append(request)
        if self.crash_at == len(self.calls):
            raise RuntimeError("simulated crash boundary")
        return self.results[len(self.calls) - 1]


def prepared(tmp_path):
    values = authority()
    _, manifest, _, resolution, authorization = values
    root = tmp_path / "trusted-state"
    registry = build_test_registry(authorization, manifest, resolution)
    capability = secure_execution._internal_execution_context(
        root, registry["registry_sha256"]
    )
    (root / "artifacts").mkdir(parents=True)
    (root / "states").mkdir(parents=True)
    (root / "approval_registry.json").write_text(json.dumps(registry))
    entry = registry["entries"][0]
    (root / entry["authorization_file"]).write_text(json.dumps(authorization))
    (root / entry["resolution_file"]).write_text(json.dumps(resolution))
    ledger = root / entry["state_file"]
    genesis = secure_execution.build_genesis_record(
        authorization, manifest, resolution
    )
    ledger.write_text(json.dumps(genesis) + "\n")
    return (*values, capability, ledger)


def run(values, transport):
    schedule, manifest, provenance, resolution, authorization, capability, ledger = values
    del resolution, ledger
    return secure_execution._execute_bounded_internal_once(
        capability,
        authorization["execution_authorization_id"],
        manifest,
        schedule,
        provenance,
        transport,
    )


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def build_test_registry(authorization, manifest, resolution):
    genesis = secure_execution.build_genesis_record(
        authorization, manifest, resolution
    )
    auth_hash = authorization["authorization_sha256"]
    entry = {
        "execution_authorization_id": authorization["execution_authorization_id"],
        "authorization_sha256": auth_hash,
        "manifest_sha256": manifest["manifest_sha256"],
        "resolution_artifact_sha256": resolution["artifact_sha256"],
        "provider": "the-odds-api",
        "authorization_file": f"artifacts/{auth_hash}.authorization.json",
        "resolution_file": f"artifacts/{resolution['artifact_sha256']}.resolution.json",
        "state_file": secure_execution.canonical_state_name(auth_hash),
        "genesis_record_sha256": genesis["record_sha256"],
    }
    base = {
        "schema_version": 1,
        "registry_version": secure_execution.REGISTRY_VERSION,
        "entries": [entry],
    }
    return {**base, "registry_sha256": digest(base)}


def rehash_authorization(value):
    material = {key: item for key, item in value.items() if key != "authorization_sha256"}
    value["authorization_sha256"] = digest(material)


def rehash_resolution(value):
    material = {key: item for key, item in value.items() if key != "artifact_sha256"}
    value["artifact_sha256"] = digest(material)


def test_one_time_success_and_reload_replay_make_at_most_six_calls(tmp_path):
    values = prepared(tmp_path)
    transport = FakeTransport()
    assert len(run(values, transport)) == len(transport.calls) == 6
    replay = FakeTransport()
    with pytest.raises(ExecutionBoundaryError, match="unused|consumed"):
        run(values, replay)
    assert replay.calls == []
    records = secure_execution._read_records(values[-1])
    entry = secure_execution._registry(values[5])[1][0]
    status = secure_execution.validate_ledger(records, entry, values[4])
    assert status.state == "COMPLETED" and len(status.completed) == 6


def test_partial_failure_is_explicit_and_cannot_resume_or_replay(tmp_path):
    values = prepared(tmp_path)
    transport = FakeTransport([
        TransportResult(True, 1), TransportResult(True, 1), TransportResult(False, 1)
    ])
    with pytest.raises(ExecutionBoundaryError) as error:
        run(values, transport)
    assert error.value.attempted == 3 and len(transport.calls) == 3
    records = secure_execution._read_records(values[-1])
    entry = secure_execution._registry(values[5])[1][0]
    status = secure_execution.validate_ledger(records, entry, values[4])
    assert len(status.completed) == 2 and len(status.failed) == 1
    assert len(status.untouched) == 3 and status.state == "FAILED_PARTIAL"
    replay = FakeTransport()
    with pytest.raises(ExecutionBoundaryError):
        run(values, replay)
    assert replay.calls == []


@pytest.mark.parametrize("crash_at", [1, 3])
def test_crash_boundary_is_indeterminate_and_non_replayable(tmp_path, crash_at):
    values = prepared(tmp_path)
    transport = FakeTransport(crash_at=crash_at)
    with pytest.raises(ExecutionBoundaryError, match="indeterminate"):
        run(values, transport)
    records = secure_execution._read_records(values[-1])
    entry = secure_execution._registry(values[5])[1][0]
    status = secure_execution.validate_ledger(records, entry, values[4])
    assert len(status.attempted_indeterminate) == 1
    replay = FakeTransport()
    with pytest.raises(ExecutionBoundaryError):
        run(values, replay)
    assert replay.calls == []


@pytest.mark.parametrize("bad", ["", "   ", 123, object(), "bad/event"])
def test_malformed_event_ids_are_rejected(bad):
    _, manifest, _, _, _ = authority()
    ids = [f"event-{index // 2}" for index in range(6)]
    ids[0] = bad
    with pytest.raises(ExecutionBoundaryError):
        build_resolution_artifact(
            manifest, ids, resolution_method="test", resolution_source="fixture",
            approved_by="reviewer",
        )


def test_cross_game_reuse_unapproved_and_tampered_resolution_fail():
    _, manifest, _, resolution, _ = authority()
    changed = deepcopy(resolution)
    changed["bindings"][2]["provider_event_id"] = "event-0"
    changed["bindings"][3]["provider_event_id"] = "event-0"
    rehash_resolution(changed)
    with pytest.raises(ExecutionBoundaryError, match="crosses games"):
        validate_resolution_artifact(changed, manifest)
    for field, value in (("approval_status", "PENDING"), ("approved_by", "")):
        changed = deepcopy(resolution)
        changed[field] = value
        rehash_resolution(changed)
        with pytest.raises(ExecutionBoundaryError):
            validate_resolution_artifact(changed, manifest)


def test_reordered_duplicate_substituted_and_seventh_authority_fail():
    _, manifest, _, resolution, authorization = authority()
    mutations = []
    reordered = deepcopy(authorization)
    reordered["sample_item_ids"].reverse()
    mutations.append(reordered)
    duplicate = deepcopy(authorization)
    duplicate["sample_item_ids"][1] = duplicate["sample_item_ids"][0]
    mutations.append(duplicate)
    substituted = deepcopy(authorization)
    substituted["provider_event_bindings"][0]["sample_item_id"] = "other"
    mutations.append(substituted)
    seventh = deepcopy(authorization)
    seventh["sample_item_ids"].append(seventh["sample_item_ids"][0])
    seventh["maximum_acquisition_attempts"] = 7
    mutations.append(seventh)
    for changed in mutations:
        rehash_authorization(changed)
        with pytest.raises(ExecutionBoundaryError):
            validate_execution_authorization(changed, manifest, resolution)


@pytest.mark.parametrize(
    "result",
    [
        TransportResult(False, 1, retry_required=True),
        TransportResult(False, 1, pagination_required=True),
        TransportResult(False, 1, fallback_required=True),
        TransportResult(False, 1, discovery_required=True),
        TransportResult(True, 2),
    ],
)
def test_transport_expansion_stops_after_one_interaction(tmp_path, result):
    values = prepared(tmp_path)
    transport = FakeTransport([result])
    with pytest.raises(ExecutionBoundaryError):
        run(values, transport)
    assert len(transport.calls) == 1


def test_mutable_inputs_are_snapshotted_before_transport(tmp_path):
    values = list(prepared(tmp_path))

    class MutatingTransport(FakeTransport):
        def send_once(self, request):
            values[1]["items"][0]["market"] = "alternate-market"
            return super().send_once(request)

    transport = MutatingTransport()
    run(values, transport)
    assert {request.market for request in transport.calls} == {"player_anytime_td"}


def test_duplicate_json_keys_are_rejected():
    with pytest.raises(ExecutionBoundaryError, match="duplicate JSON key"):
        strict_json_loads('{"schema_version":1,"schema_version":2}')


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_authority_json_is_rejected(constant):
    with pytest.raises(ExecutionBoundaryError, match="non-finite"):
        strict_json_loads('{"value":' + constant + "}")


def test_nonfinite_registry_resolution_authorization_and_ledger_fail(tmp_path):
    values = prepared(tmp_path)
    capability = values[5]
    registry_path = capability.state_root / "approval_registry.json"
    registry_path.write_text('{"value":NaN}')
    with pytest.raises(ExecutionBoundaryError, match="non-finite"):
        secure_execution._registry(capability)

    for name, constant in (("authorization", "NaN"), ("resolution", "Infinity")):
        path = tmp_path / f"{name}.json"
        path.write_text('{"value":' + constant + "}")
        with pytest.raises(ExecutionBoundaryError, match="non-finite"):
            secure_execution.load_strict_json(path)

    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"value":-Infinity}\n')
    with pytest.raises(ExecutionBoundaryError, match="non-finite"):
        secure_execution._read_records(ledger)


def test_production_absent_rejects_original_global_assignment_exploit(
    tmp_path, monkeypatch
):
    values = prepared(tmp_path)
    transport = FakeTransport()
    monkeypatch.setattr(secure_execution, "STATE_ROOT", tmp_path / "attacker-root", raising=False)
    monkeypatch.setattr(
        secure_execution,
        "TRUSTED_REGISTRY_SHA256",
        values[5].registry_sha256,
        raising=False,
    )
    with pytest.raises(ExecutionBoundaryError, match="disabled"):
        secure_execution.execute_registered_once(
            values[4]["execution_authorization_id"],
            values[1],
            values[0],
            values[2],
            transport,
        )
    assert transport.calls == []


def test_configuration_environment_and_registry_cannot_enable_production(
    tmp_path, monkeypatch
):
    values = prepared(tmp_path)
    transport = FakeTransport()
    monkeypatch.setenv("GRIDIRON_PLAYER_TD_AUTHORITY", str(values[5].state_root))
    monkeypatch.setattr(
        secure_execution,
        "DEPLOYMENT_AUTHORITY_FILE",
        values[5].state_root / "approval_registry.json",
        raising=False,
    )
    monkeypatch.setattr(
        secure_execution, "PRODUCTION_AUTHORITY", values[5], raising=False
    )
    with pytest.raises(ExecutionBoundaryError, match="disabled"):
        secure_execution.execute_registered_once(
            values[4]["execution_authorization_id"],
            values[1],
            values[0],
            values[2],
            transport,
        )
    assert transport.calls == []


def test_production_entry_rejects_internal_context_argument(tmp_path):
    values = prepared(tmp_path)
    transport = FakeTransport()
    with pytest.raises(TypeError):
        secure_execution.execute_registered_once(
            values[4]["execution_authorization_id"],
            values[1],
            values[0],
            values[2],
            transport,
            authority=values[5],
        )
    assert transport.calls == []


def test_two_caller_selected_roots_cannot_reach_production(tmp_path, monkeypatch):
    values = prepared(tmp_path)
    for suffix in ("one", "two"):
        transport = FakeTransport()
        monkeypatch.setattr(
            secure_execution, "STATE_ROOT", tmp_path / suffix, raising=False
        )
        monkeypatch.setattr(
            secure_execution,
            "TRUSTED_REGISTRY_SHA256",
            values[5].registry_sha256,
            raising=False,
        )
        with pytest.raises(ExecutionBoundaryError, match="disabled"):
            secure_execution.execute_registered_once(
                values[4]["execution_authorization_id"],
                values[1],
                values[0],
                values[2],
                transport,
            )
        assert transport.calls == []


def test_missing_canonical_state_fails_closed_without_transport(tmp_path):
    values = prepared(tmp_path)
    values[-1].unlink()
    transport = FakeTransport()
    with pytest.raises(ExecutionBoundaryError, match="missing"):
        run(values, transport)
    assert transport.calls == []


@pytest.mark.parametrize("replacement", ["", '{"sequence":'])
def test_empty_or_truncated_state_fails_closed_without_transport(
    tmp_path, replacement
):
    values = prepared(tmp_path)
    values[-1].write_text(replacement)
    transport = FakeTransport()
    with pytest.raises((ExecutionBoundaryError, json.JSONDecodeError)):
        run(values, transport)
    assert transport.calls == []


@pytest.mark.parametrize("mutation", ["delete", "replace"])
def test_state_loss_after_claim_before_started_fails_without_transport(
    tmp_path, monkeypatch, mutation
):
    values = prepared(tmp_path)
    ledger = values[-1]
    original_append = secure_execution._append_existing

    def mutate_before_append(path, identity, records, record):
        if mutation == "delete":
            path.unlink()
        else:
            replacement = path.with_suffix(".replacement")
            replacement.write_bytes(path.read_bytes())
            os.replace(replacement, path)
        return original_append(path, identity, records, record)

    monkeypatch.setattr(secure_execution, "_append_existing", mutate_before_append)
    transport = FakeTransport()
    with pytest.raises(ExecutionBoundaryError, match="disappeared|replaced"):
        run(values, transport)
    assert transport.calls == []
    if mutation == "delete":
        assert not ledger.exists()


@pytest.mark.parametrize("mutation", ["delete", "replace"])
def test_state_loss_after_attempt_record_fails_before_transport(
    tmp_path, monkeypatch, mutation
):
    values = prepared(tmp_path)
    ledger = values[-1]
    original_append = secure_execution._append_existing
    append_count = 0

    def mutate_after_attempt(path, identity, records, record):
        nonlocal append_count
        original_append(path, identity, records, record)
        append_count += 1
        if append_count == 2:
            if mutation == "delete":
                path.unlink()
            else:
                replacement = path.with_suffix(".replacement")
                replacement.write_bytes(path.read_bytes())
                os.replace(replacement, path)

    monkeypatch.setattr(secure_execution, "_append_existing", mutate_after_attempt)
    transport = FakeTransport()
    with pytest.raises(ExecutionBoundaryError, match="disappeared|replaced"):
        run(values, transport)
    assert transport.calls == []
    if mutation == "delete":
        assert not ledger.exists()


def test_state_loss_during_transport_is_indeterminate_and_not_recreated(tmp_path):
    values = prepared(tmp_path)
    ledger = values[-1]

    class DeletingTransport(FakeTransport):
        def send_once(self, request):
            result = super().send_once(request)
            ledger.unlink()
            return result

    transport = DeletingTransport()
    with pytest.raises(ExecutionBoundaryError, match="continuity.*indeterminate") as error:
        run(values, transport)
    assert error.value.attempted == 1
    assert len(transport.calls) == 1
    assert not ledger.exists()


def test_append_existing_cannot_create_missing_ledger(tmp_path):
    values = prepared(tmp_path)
    ledger = values[-1]
    stat = ledger.stat()
    bound = secure_execution._LedgerIdentity(stat.st_dev, stat.st_ino)
    missing = tmp_path / "missing.jsonl"
    with pytest.raises(ExecutionBoundaryError, match="disappeared"):
        secure_execution._append_existing(missing, bound, [], {"state": "STARTED"})
    assert not missing.exists()


def test_reconstructed_authorization_uses_same_global_state(tmp_path):
    values = list(prepared(tmp_path))
    run(values, FakeTransport())
    values[4] = json.loads(json.dumps(values[4]))
    replay = FakeTransport()
    with pytest.raises(ExecutionBoundaryError, match="started|consumed"):
        run(values, replay)
    assert replay.calls == []


def test_fake_rehashed_registry_cannot_replace_pinned_authority(tmp_path):
    values = prepared(tmp_path)
    registry_path = values[5].state_root / "approval_registry.json"
    registry = json.loads(registry_path.read_text())
    registry["entries"][0]["provider"] = "caller-provider"
    material = {key: value for key, value in registry.items() if key != "registry_sha256"}
    registry["registry_sha256"] = digest(material)
    registry_path.write_text(json.dumps(registry))
    transport = FakeTransport()
    with pytest.raises(ExecutionBoundaryError, match="not trusted"):
        run(values, transport)
    assert transport.calls == []


def test_concurrent_global_claim_allows_only_one_executor(tmp_path):
    values = prepared(tmp_path)
    transports = (FakeTransport(), FakeTransport())

    def invoke(index):
        try:
            run(values, transports[index])
            return "OK"
        except ExecutionBoundaryError:
            return "REJECTED"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(invoke, (0, 1)))
    assert sorted(outcomes) == ["OK", "REJECTED"]
    assert sorted(len(transport.calls) for transport in transports) == [0, 6]


def _rehash_ledger(records):
    previous = "0" * 64
    for sequence, record in enumerate(records):
        record["sequence"] = sequence
        record["previous_record_sha256"] = previous
        material = {key: value for key, value in record.items() if key != "record_sha256"}
        record["record_sha256"] = digest(material)
        previous = record["record_sha256"]


@pytest.mark.parametrize("mutation", [
    lambda records: records[1].__setitem__("state", "UNKNOWN"),
    lambda records: records[2].__setitem__("attempt_id", "f" * 64),
    lambda records: records[2].__setitem__("sample_item_id", "other"),
    lambda records: records.insert(3, deepcopy(records[2])),
    lambda records: records.__setitem__(slice(2, 4), list(reversed(records[2:4]))),
    lambda records: records.append(deepcopy(records[-1])),
])
def test_rehashed_ledger_tampering_fails_state_machine(tmp_path, mutation):
    values = prepared(tmp_path)
    run(values, FakeTransport())
    records = [json.loads(line) for line in values[-1].read_text().splitlines()]
    mutation(records)
    _rehash_ledger(records)
    entry = secure_execution._registry(values[5])[1][0]
    with pytest.raises(ExecutionBoundaryError):
        secure_execution.validate_ledger(records, entry, values[4])
