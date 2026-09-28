from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from gridiron.market.player_td_acquisition import (
    PlayerTDAcquisitionError,
    execute_bounded_acquisition,
)
from gridiron.market.player_td_authorized_execution import execute_registered_once
from gridiron.market.player_td_execution import ExecutionBoundaryError
from gridiron.market.player_td_historical_authority import (
    AUTHORITY_TYPE,
    FROZEN_MANIFEST_SHA256,
    HistoricalAuthorityError,
    build_historical_authority,
    execute_historical_validation_sample_once,
    historical_execution_identity,
    historical_raw_destination,
    validate_historical_authority,
)
from gridiron.market.player_td_sample import PlayerTDSampleError

ROOT = Path("data/reference/player_td_sample_v1")


def frozen_inputs():
    manifest = json.loads((ROOT / "step93c_player_td_sample_manifest.json").read_text())
    schedule = json.loads((ROOT / "player_td_schedule_2023_2025_v1.json").read_text())
    provenance = json.loads((ROOT / "schedule_provenance.json").read_text())
    artifact = json.loads((ROOT / "step93j1_historical_authority.json").read_text())
    return manifest, schedule, provenance, artifact


def digest(value):
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def rehash_manifest(manifest, item_index=None):
    if item_index is not None:
        item = manifest["items"][item_index]
        material = {key: value for key, value in item.items() if key != "sample_item_id"}
        item["sample_item_id"] = digest(material)
    material = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    manifest["manifest_sha256"] = digest(material)


def rehash_authority(artifact):
    material = {
        key: value for key, value in artifact.items() if key != "authority_sha256"
    }
    artifact["authority_sha256"] = digest(material)


class FakeTransport:
    def __init__(self):
        self.calls = []

    def send_once(self, request):
        self.calls.append(request)
        raise AssertionError("disabled authority reached transport")


def test_exact_frozen_manifest_builds_committed_deterministic_authority():
    manifest, schedule, provenance, committed = frozen_inputs()
    first = build_historical_authority(manifest, schedule, provenance)
    assert first == committed
    assert first == build_historical_authority(manifest, schedule, provenance)
    assert first["authority_type"] == AUTHORITY_TYPE
    assert first["manifest_sha256"] == FROZEN_MANIFEST_SHA256
    assert first["item_count"] == first["maximum_request_count"] == 6
    assert first["execution_enabled"] is False
    validate_historical_authority(first)


def test_changed_manifest_hash_is_rejected():
    manifest, schedule, provenance, _ = frozen_inputs()
    manifest["manifest_sha256"] = "f" * 64
    with pytest.raises(PlayerTDSampleError):
        build_historical_authority(manifest, schedule, provenance)


@pytest.mark.parametrize(
    "mutation,item_index",
    [
        (lambda value: value["items"][0].__setitem__("market", "alternate"), 0),
        (lambda value: value["items"][0].__setitem__("region", "eu"), 0),
        (lambda value: value["items"][0].__setitem__("odds_format", "decimal"), 0),
        (lambda value: value["items"][0].__setitem__("books", ["draftkings"]), 0),
        (lambda value: value["items"][0].__setitem__("season", 2026), 0),
        (lambda value: value["items"][0].__setitem__("canonical_game_id", "2026_01_X_Y"), 0),
        (lambda value: value["items"].append(deepcopy(value["items"][0])), None),
    ],
)
def test_changed_item_scope_and_seventh_item_are_rejected(mutation, item_index):
    manifest, schedule, provenance, _ = frozen_inputs()
    mutation(manifest)
    rehash_manifest(manifest, item_index)
    with pytest.raises(PlayerTDSampleError):
        build_historical_authority(manifest, schedule, provenance)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 2),
        ("authority_type", "OTHER"),
        ("market", "alternate"),
        ("region", "eu"),
        ("odds_format", "decimal"),
        ("bookmakers", ["draftkings"]),
        ("maximum_request_count", 7),
        ("execution_enabled", True),
    ],
)
def test_rehashed_authority_scope_mutations_are_rejected(field, value):
    _, _, _, artifact = frozen_inputs()
    artifact[field] = value
    rehash_authority(artifact)
    with pytest.raises(HistoricalAuthorityError):
        validate_historical_authority(artifact)


def test_artifact_cannot_self_authorize_and_environment_cannot_activate(monkeypatch):
    manifest, schedule, provenance, artifact = frozen_inputs()
    transport = FakeTransport()
    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "unused-test-value")
    monkeypatch.setenv("GRIDIRON_PLAYER_TD_AUTHORITY_SHA256", artifact["authority_sha256"])
    with pytest.raises(ExecutionBoundaryError, match="disabled"):
        execute_historical_validation_sample_once(
            artifact,
            manifest,
            schedule,
            provenance,
            transport,
            trusted_hash=artifact["authority_sha256"],
        )
    assert transport.calls == []


def test_existing_public_tombstones_and_new_entry_are_zero_call():
    manifest, schedule, provenance, artifact = frozen_inputs()
    transport = FakeTransport()
    with pytest.raises(ExecutionBoundaryError, match="disabled"):
        execute_registered_once("none", manifest, schedule, provenance, transport)
    with pytest.raises(PlayerTDAcquisitionError, match="disabled"):
        execute_bounded_acquisition(manifest, schedule, provenance, (), transport.send_once)
    with pytest.raises(ExecutionBoundaryError, match="disabled"):
        execute_historical_validation_sample_once(artifact, transport)
    assert transport.calls == []


def test_raw_destination_is_deterministic_historical_and_outside_operational():
    manifest, _, _, artifact = frozen_inputs()
    item_id = manifest["items"][0]["sample_item_id"]
    first = historical_raw_destination(artifact, item_id)
    assert first == historical_raw_destination(artifact, item_id)
    assert first.response_path.as_posix().startswith("data/research/player_td_validation/")
    assert "operational" not in first.response_path.parts
    assert first.response_path.name == f"{item_id}.response.json"
    assert first.metadata_path.name == f"{item_id}.metadata.json"
    assert not first.response_path.exists() and not first.metadata_path.exists()


def test_future_execution_identity_binds_authority_and_manifest_hashes():
    _, _, _, artifact = frozen_inputs()
    identity = historical_execution_identity(artifact)
    assert len(identity) == 64
    assert identity == historical_execution_identity(artifact)


def test_step93j1_module_has_no_network_or_credential_access():
    source = Path(
        "src/gridiron/market/player_td_historical_authority.py"
    ).read_text(encoding="utf-8")
    prohibited = (
        "import requests", "import httpx", "import socket", "urllib",
        "GRIDIRON_ODDS_API_KEY", "os.environ", "send_once(",
    )
    assert all(token not in source for token in prohibited)
