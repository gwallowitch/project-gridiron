from __future__ import annotations

import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

from gridiron.market.player_td_second_attempt_authority import (
    SecondAttemptAuthorityError,
    build_second_attempt_authority,
    validate_second_attempt_authority,
)

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data/reference/player_td_sample_v1"
ARTIFACT = REFERENCE / "step93j5_second_attempt_authority.json"
PREDECESSOR_ID = "e61e72001013bcd24a96ceb0e779cb6d4f7969901afc453bfbef6917120e1567"


def _load(name: str) -> dict[str, object]:
    return json.loads((REFERENCE / name).read_text(encoding="utf-8"))


def _artifact() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _binding() -> dict[str, object]:
    artifact = _artifact()
    return {
        "execution_identity": artifact["predecessor_execution_identity"],
        "terminal_state": artifact["predecessor_terminal_state"],
        "terminal_record_sha256": artifact["predecessor_terminal_record_sha256"],
        "ledger_sha256": artifact["predecessor_ledger_sha256"],
        "claim_sha256": artifact["predecessor_claim_sha256"],
        "raw_response_sha256": artifact["predecessor_raw_response_sha256"],
        "metadata_sha256": artifact["predecessor_metadata_sha256"],
        "failure_classification": artifact["predecessor_failure_classification"],
        "provider_result": artifact["predecessor_provider_result"],
    }


def _build() -> dict[str, object]:
    return build_second_attempt_authority(
        _load("step93c_player_td_sample_manifest.json"),
        _load("step93j1_historical_authority.json"),
        _load("step93j1a_historical_event_resolution_authority.json"),
        _binding(),
    )


def test_frozen_artifact_is_exact_and_deterministic() -> None:
    first = _build()
    second = _build()
    assert first == second == _artifact()
    validate_second_attempt_authority(first)
    assert first["second_attempt_execution_identity"] != PREDECESSOR_ID


def test_exact_scope_and_disabled_execution() -> None:
    artifact = _artifact()
    assert artifact["manifest_sha256"] == (
        "b120ac96101f01846906a66eab1987cfa57dbfbbd742e58384fb1f5f4edda927"
    )
    assert artifact["attd_authority_sha256"] == (
        "4f7f3baab797051909c284f30102254e5d9f2f255e30ffb24c077bf984c2dd77"
    )
    assert artifact["event_authority_sha256"] == (
        "d8136aab1a1915ca99cc1b6cb5bf8bff113ae06fd32c67238423305beebfc980"
    )
    assert len(artifact["discovery_plan"]) == 3
    assert len(artifact["market_plan"]) == 6
    assert artifact["maximum_discovery_operations"] == 3
    assert artifact["maximum_market_operations"] == 6
    assert artifact["maximum_combined_provider_operations"] == 9
    assert artifact["execution_enabled"] is False
    assert artifact["execution_precondition"] == (
        "HUMAN_CONFIRMED_PAID_HISTORICAL_ACCESS"
    )
    assert artifact["historical_content_availability"] == (
        "UNVERIFIED_UNTIL_ACQUISITION"
    )
    assert artifact["incomplete_evidence_behavior"] == "PRESERVE_AND_FAIL_CLOSED"
    assert {item["market"] for item in artifact["market_plan"]} == {
        "player_anytime_td"
    }
    assert {tuple(item["bookmakers"]) for item in artifact["market_plan"]} == {
        ("draftkings", "fanduel", "betmgm")
    }


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("predecessor_execution_identity", "0" * 64),
        ("predecessor_terminal_record_sha256", "0" * 64),
        ("predecessor_ledger_sha256", "0" * 64),
        ("manifest_sha256", "0" * 64),
        ("maximum_combined_provider_operations", 10),
        ("execution_enabled", True),
        ("historical_content_availability", "AVAILABLE"),
        ("state_root", "data/research/player_td_validation/step93c_sample/execution"),
    ],
)
def test_authority_mutations_fail_closed(field: str, replacement: object) -> None:
    mutated = copy.deepcopy(_artifact())
    mutated[field] = replacement
    with pytest.raises(SecondAttemptAuthorityError):
        validate_second_attempt_authority(mutated)


def test_market_or_discovery_scope_cannot_change() -> None:
    for field in ("market_plan", "discovery_plan"):
        mutated = copy.deepcopy(_artifact())
        mutated[field] = mutated[field][:-1]
        with pytest.raises(SecondAttemptAuthorityError):
            validate_second_attempt_authority(mutated)


def test_arbitrary_predecessor_cannot_build_authority() -> None:
    binding = _binding()
    binding["execution_identity"] = "f" * 64
    with pytest.raises(SecondAttemptAuthorityError):
        build_second_attempt_authority(
            _load("step93c_player_td_sample_manifest.json"),
            _load("step93j1_historical_authority.json"),
            _load("step93j1a_historical_event_resolution_authority.json"),
            binding,
        )


def test_authority_import_and_validation_are_credential_and_network_inert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("credential or network access is forbidden")

    monkeypatch.setattr("os.environ.get", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    module_name = "gridiron.market.player_td_second_attempt_authority"
    module = importlib.reload(sys.modules[module_name])
    module.validate_second_attempt_authority(_artifact())


def test_second_attempt_paths_do_not_collide_with_consumed_attempt() -> None:
    artifact = _artifact()
    old_root = "data/research/player_td_validation/step93c_sample/execution"
    for field in (
        "second_attempt_root",
        "state_root",
        "event_evidence_root",
        "market_evidence_root",
    ):
        assert artifact[field] != old_root
        assert "/attempt2" in artifact[field]


def test_reference_artifact_bytes_have_stable_hash() -> None:
    first = ARTIFACT.read_bytes()
    second = ARTIFACT.read_bytes()
    assert first == second
    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()
