from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from gridiron.market.player_td_acquisition import (
    PlayerTDAcquisitionError,
    ResolvedSampleAuthorization,
    build_bounded_acquisition_plan,
    execute_bounded_acquisition,
)
from gridiron.market.player_td_sample import (
    PlayerTDSampleError,
    validate_frozen_sample_manifest,
)
from gridiron.market.player_td_schedule import (
    PlayerTDScheduleError,
    validate_derived_schedule,
)

ROOT = Path("data/reference/player_td_sample_v1")


def _load_authority():
    schedule = json.loads((ROOT / "player_td_schedule_2023_2025_v1.json").read_text())
    manifest = json.loads((ROOT / "step93c_player_td_sample_manifest.json").read_text())
    provenance = json.loads((ROOT / "schedule_provenance.json").read_text())
    return schedule, manifest, provenance


def _digest(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _rehash(manifest: dict, item_index: int | None = None) -> None:
    if item_index is not None:
        item = manifest["items"][item_index]
        material = {key: value for key, value in item.items() if key != "sample_item_id"}
        item["sample_item_id"] = _digest(material)
    material = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    manifest["manifest_sha256"] = _digest(material)


def test_frozen_authority_positive_replay_is_deterministic():
    schedule, manifest, provenance = _load_authority()
    validate_frozen_sample_manifest(manifest, schedule, provenance)
    validate_frozen_sample_manifest(deepcopy(manifest), deepcopy(schedule), provenance)


@pytest.mark.parametrize(
    "mutation,item_index",
    [
        (lambda value: value["items"][0].__setitem__("canonical_game_id", "other"), 0),
        (
            lambda value: value["items"][0].__setitem__(
                "requested_snapshot_at", "2023-09-07T12:21:00Z"
            ),
            0,
        ),
        (lambda value: value["items"].reverse(), None),
        (lambda value: value["items"][0].__setitem__("final_home_score", 20), 0),
        (lambda value: value.__setitem__("maximum_request_count", 7), None),
        (lambda value: value.__setitem__("estimated_maximum_credits", 70), None),
    ],
)
def test_consistently_rehashed_manifest_mutations_fail(mutation, item_index):
    schedule, manifest, provenance = _load_authority()
    mutation(manifest)
    _rehash(manifest, item_index)
    with pytest.raises(PlayerTDSampleError):
        validate_frozen_sample_manifest(manifest, schedule, provenance)


def test_changed_provenance_fails_even_when_manifest_is_unchanged():
    schedule, manifest, provenance = _load_authority()
    provenance["source_asset_id"] = 1
    with pytest.raises(PlayerTDSampleError, match="provenance"):
        validate_frozen_sample_manifest(manifest, schedule, provenance)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows.pop(),
        lambda rows: rows.append(deepcopy(rows[-1])),
        lambda rows: rows.__setitem__(272, {**rows[272], "season": 2023}),
        lambda rows: rows.__setitem__(1, deepcopy(rows[0])),
        lambda rows: rows[0].__setitem__("final_home_score", 20),
    ],
)
def test_derived_schedule_population_and_identity_mutations_fail(mutation):
    schedule, _, _ = _load_authority()
    mutation(schedule)
    with pytest.raises(PlayerTDScheduleError):
        validate_derived_schedule(schedule)


def test_altered_schedule_kickoff_fails_frozen_identity():
    schedule, manifest, provenance = _load_authority()
    schedule[0]["kickoff_at"] = "2023-09-08T00:21:00Z"
    with pytest.raises(PlayerTDSampleError, match="schedule identity"):
        validate_frozen_sample_manifest(manifest, schedule, provenance)


def _authorizations(manifest):
    return tuple(
        ResolvedSampleAuthorization(item["sample_item_id"], f"event-{index}")
        for index, item in enumerate(manifest["items"])
    )


def test_unresolved_event_ids_stop_before_any_transport_exists():
    with pytest.raises(PlayerTDAcquisitionError, match="resolved"):
        ResolvedSampleAuthorization("item", "")


def test_authorization_substitution_and_seventh_authorization_fail():
    schedule, manifest, provenance = _load_authority()
    authorizations = list(_authorizations(manifest))
    authorizations[0] = ResolvedSampleAuthorization("unauthorized", "event-x")
    with pytest.raises(PlayerTDAcquisitionError, match="one-to-one"):
        build_bounded_acquisition_plan(
            manifest, schedule, provenance, authorizations
        )
    authorizations = list(_authorizations(manifest))
    authorizations.append(authorizations[0])
    with pytest.raises(PlayerTDAcquisitionError, match="exactly six"):
        build_bounded_acquisition_plan(
            manifest, schedule, provenance, authorizations
        )


def test_reusable_executor_is_disabled():
    schedule, manifest, provenance = _load_authority()
    with pytest.raises(PlayerTDAcquisitionError, match="disabled"):
        execute_bounded_acquisition(
            manifest, schedule, provenance, _authorizations(manifest), lambda request: None
        )
