from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from gridiron.market.player_td_event_resolution_authority import (
    AUTHORITY_TYPE,
    EventResolutionAuthorityError,
    build_event_resolution_authority,
    event_resolution_destination,
    validate_event_resolution_authority,
)
from gridiron.market.player_td_historical_authority import (
    build_historical_authority,
)

ROOT = Path("data/reference/player_td_sample_v1")
MANIFEST_PATH = ROOT / "step93c_player_td_sample_manifest.json"
J1_PATH = ROOT / "step93j1_historical_authority.json"
J1A_PATH = ROOT / "step93j1a_historical_event_resolution_authority.json"
SCHEDULE_PATH = ROOT / "player_td_schedule_2023_2025_v1.json"
PROVENANCE_PATH = ROOT / "schedule_provenance.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def rehash_authority(artifact: dict) -> None:
    material = {key: value for key, value in artifact.items() if key != "authority_sha256"}
    artifact["authority_sha256"] = digest(material)


def test_exact_frozen_scope_builds_committed_deterministic_authority():
    manifest = load(MANIFEST_PATH)
    committed = load(J1A_PATH)
    first = build_event_resolution_authority(manifest)
    assert first == committed
    assert first == build_event_resolution_authority(manifest)
    assert first["authority_type"] == AUTHORITY_TYPE
    assert first["authority_sha256"] == (
        "d8136aab1a1915ca99cc1b6cb5bf8bff113ae06fd32c67238423305beebfc980"
    )
    assert first["game_count"] == first["maximum_discovery_request_count"] == 3
    assert first["execution_enabled"] is False
    validate_event_resolution_authority(first)


def test_frozen_three_games_and_dates_are_exact():
    games = load(J1A_PATH)["games"]
    assert [game["canonical_game_id"] for game in games] == [
        "2023_01_DET_KC",
        "2024_01_BAL_KC",
        "2025_01_DAL_PHI",
    ]
    assert [game["discovery_date"] for game in games] == [
        "2023-09-07T12:20:00Z",
        "2024-09-05T12:20:00Z",
        "2025-09-04T12:20:00Z",
    ]


def test_changed_manifest_and_fourth_game_are_rejected():
    manifest = load(MANIFEST_PATH)
    changed = deepcopy(manifest)
    changed["items"][0]["home_team"] = "OTHER"
    material = {key: value for key, value in changed.items() if key != "manifest_sha256"}
    changed["manifest_sha256"] = digest(material)
    with pytest.raises(EventResolutionAuthorityError):
        build_event_resolution_authority(changed)

    fourth = deepcopy(manifest)
    fourth["items"].append(deepcopy(fourth["items"][0]))
    material = {key: value for key, value in fourth.items() if key != "manifest_sha256"}
    fourth["manifest_sha256"] = digest(material)
    with pytest.raises(EventResolutionAuthorityError):
        build_event_resolution_authority(fourth)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["games"][0].__setitem__("canonical_game_id", "2026_01_X_Y"),
        lambda value: value["games"][0].__setitem__("away_team", "OTHER"),
        lambda value: value["games"][0].update(
            away_team=value["games"][0]["home_team"],
            home_team=value["games"][0]["away_team"],
        ),
        lambda value: value["games"][0].__setitem__(
            "kickoff_at", "2023-09-08T00:21:00Z"
        ),
        lambda value: value["games"][0].__setitem__(
            "discovery_date", "2023-09-07T12:21:00Z"
        ),
        lambda value: value.__setitem__("sport", "americanfootball_ncaaf"),
        lambda value: value.__setitem__("endpoint_class", "CURRENT_EVENTS"),
        lambda value: value.__setitem__("maximum_discovery_request_count", 4),
        lambda value: value.__setitem__("execution_enabled", True),
    ],
)
def test_rehashed_scope_mutations_fail_closed(mutation):
    artifact = load(J1A_PATH)
    mutation(artifact)
    rehash_authority(artifact)
    with pytest.raises(EventResolutionAuthorityError):
        validate_event_resolution_authority(artifact)


def test_caller_cannot_select_arbitrary_date_or_nonmember_destination():
    artifact = load(J1A_PATH)
    with pytest.raises(TypeError):
        build_event_resolution_authority(load(MANIFEST_PATH), date="arbitrary")
    with pytest.raises(EventResolutionAuthorityError):
        event_resolution_destination(artifact, "2025_02_OTHER_GAME")


def test_future_raw_destinations_are_deterministic_and_outside_operational():
    artifact = load(J1A_PATH)
    for game in artifact["games"]:
        destination = event_resolution_destination(
            artifact, game["canonical_game_id"]
        )
        assert destination == event_resolution_destination(
            artifact, game["canonical_game_id"]
        )
        assert destination.response_path.as_posix().startswith(
            "data/research/player_td_validation/step93c_sample/event_resolution/"
        )
        assert "operational" not in destination.response_path.parts
        assert not destination.response_path.exists()
        assert not destination.metadata_path.exists()


def test_environment_cannot_activate_or_change_authority(monkeypatch):
    artifact = load(J1A_PATH)
    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "unused-test-value")
    monkeypatch.setenv("GRIDIRON_PLAYER_TD_EVENT_AUTHORITY_SHA256", "f" * 64)
    validate_event_resolution_authority(artifact)
    assert artifact["execution_enabled"] is False


def test_existing_j1_and_step93c_artifacts_remain_exact():
    manifest = load(MANIFEST_PATH)
    schedule = load(SCHEDULE_PATH)
    provenance = load(PROVENANCE_PATH)
    j1 = load(J1_PATH)
    assert manifest["manifest_sha256"] == (
        "b120ac96101f01846906a66eab1987cfa57dbfbbd742e58384fb1f5f4edda927"
    )
    assert build_historical_authority(manifest, schedule, provenance) == j1
    assert j1["authority_sha256"] == (
        "4f7f3baab797051909c284f30102254e5d9f2f255e30ffb24c077bf984c2dd77"
    )


def test_j1a_module_has_no_network_credential_or_execution_implementation():
    source = Path(
        "src/gridiron/market/player_td_event_resolution_authority.py"
    ).read_text(encoding="utf-8")
    prohibited = (
        "import requests",
        "import httpx",
        "import socket",
        "urllib",
        "GRIDIRON_ODDS_API_KEY",
        "os.environ",
        "send_once(",
        "execute_event_resolution",
    )
    assert all(token not in source for token in prohibited)
