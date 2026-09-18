"""Official Firestore emulator validation for the Step 91X.2 adapter."""

from __future__ import annotations

import hashlib
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from google.cloud import firestore
from google.cloud.firestore_v1 import transactional

from gridiron.market.cloud_evidence import (
    CLASSIFICATION,
    CloudEvidenceError,
    FirestoreEvidenceRepository,
    ImmutableConflictError,
    LeaseUnavailableError,
    StaleLeaseError,
    build_raw_response,
    build_slot,
    logical_slot_id,
)
from gridiron.market.collection_attempts import build_collection_attempt
from gridiron.market.operational_history import canonical_json
from scripts import gridiron_cloud_candidate as candidate

EMULATOR_HOST = "127.0.0.1:8080"
FAKE_PROJECT = "demo-gridiron-step91x2a"
NOW = datetime(2026, 9, 10, 16, tzinfo=UTC)

if (
    os.environ.get("FIRESTORE_EMULATOR_HOST") != EMULATOR_HOST
    or os.environ.get("GOOGLE_CLOUD_PROJECT") != FAKE_PROJECT
):
    pytest.skip(
        "official emulator tests require the exact isolated host and fake project",
        allow_module_level=True,
    )


def _slot(game_id: str = "2026_01_DAL_PHI") -> dict[str, Any]:
    return build_slot(
        game_id=game_id,
        market_type="MONEYLINE",
        target_label="T6H",
        kickoff_at="2026-09-10T22:00:00Z",
        target_minutes=360,
        lower_bound_minutes=330,
        upper_bound_minutes=390,
    )


def _raw(slot_id: str, *, payload: object | None = None) -> dict[str, Any]:
    return build_raw_response(
        provider="the-odds-api",
        lane="MONEYLINE",
        product="h2h-us-three-book",
        requested_books=("betmgm", "fanduel", "draftkings"),
        fetched_at=NOW,
        payload=(
            [{"id": "provider-event", "bookmakers": []}]
            if payload is None
            else payload
        ),
        slot_ids=(slot_id,),
        parser_version="step91q-v1",
    )


def _identified(base: dict[str, object], field: str) -> dict[str, object]:
    return {
        **base,
        field: hashlib.sha256(canonical_json(base).encode()).hexdigest(),
    }


def _attempt(
    *, result: str, reason: str, observation_id: str | None = None
) -> dict[str, Any]:
    return build_collection_attempt(
        game_id="2026_01_DAL_PHI",
        collection_target="T6H",
        target_minutes_to_kickoff=360,
        kickoff_at="2026-09-10T22:00:00Z",
        attempted_at=NOW,
        result=result,
        reason_code=reason,
        observation_id=observation_id,
    )


@pytest.fixture
def client() -> firestore.Client:
    assert os.environ["FIRESTORE_EMULATOR_HOST"] == EMULATOR_HOST
    assert os.environ["GOOGLE_CLOUD_PROJECT"] == FAKE_PROJECT
    assert not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    return firestore.Client(project=FAKE_PROJECT)


@pytest.fixture
def repository(client: firestore.Client) -> FirestoreEvidenceRepository:
    namespace = "step91x2a_" + uuid.uuid4().hex
    return FirestoreEvidenceRepository(client, namespace=namespace)


def test_isolated_project_and_deterministic_slot_creation(
    client: firestore.Client, repository: FirestoreEvidenceRepository
) -> None:
    assert client.project == FAKE_PROJECT
    expected = hashlib.sha256(
        canonical_json(
            {
                "game_id": "2026_01_DAL_PHI",
                "market_type": "MONEYLINE",
                "target_label": "T6H",
            }
        ).encode()
    ).hexdigest()
    assert logical_slot_id("2026_01_DAL_PHI", "MONEYLINE", "T6H") == expected
    token = repository.acquire_lease(
        _slot(), owner="worker-one", now=NOW, ttl=timedelta(minutes=5)
    )
    stored = repository.inspect_slot(token.slot_id)
    assert stored["slot_id"] == expected
    assert stored["state"] == "LEASED"
    assert stored["lease_epoch"] == 1


def test_lease_contention_takeover_epoch_and_stale_owner(
    repository: FirestoreEvidenceRepository,
) -> None:
    first = repository.acquire_lease(
        _slot(), owner="worker-one", now=NOW, ttl=timedelta(minutes=5)
    )
    with pytest.raises(LeaseUnavailableError):
        repository.acquire_lease(
            _slot(), owner="worker-two", now=NOW, ttl=timedelta(minutes=5)
        )
    second = repository.acquire_lease(
        _slot(),
        owner="worker-two",
        now=NOW + timedelta(minutes=6),
        ttl=timedelta(minutes=5),
    )
    assert second.epoch == first.epoch + 1
    with pytest.raises(StaleLeaseError):
        repository.checkpoint_raw((first,), _raw(first.slot_id))


def test_raw_checkpoint_immutability_transition_and_recovery(
    repository: FirestoreEvidenceRepository,
) -> None:
    first = repository.acquire_lease(
        _slot(), owner="worker-one", now=NOW, ttl=timedelta(minutes=5)
    )
    source = _raw(first.slot_id)
    repository.checkpoint_raw((first,), source)
    repository.checkpoint_raw((first,), source)
    captured = repository.inspect_slot(first.slot_id)
    assert captured["state"] == "RAW_CAPTURED"
    assert captured["raw_response_id"] == source["raw_response_id"]
    assert repository.get_raw_response(source["raw_response_id"]) == source

    takeover = repository.acquire_lease(
        _slot(),
        owner="worker-two",
        now=NOW + timedelta(minutes=6),
        ttl=timedelta(minutes=5),
    )
    recovered = repository.inspect_slot(takeover.slot_id)
    assert takeover.epoch == 2
    assert recovered["state"] == "RAW_CAPTURED"
    assert recovered["raw_response_id"] == source["raw_response_id"]
    assert repository.get_raw_response(source["raw_response_id"])["payload"] == source["payload"]


def test_raw_captured_cloud_recovery_does_not_refetch_provider(
    repository: FirestoreEvidenceRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    game = {
        "game_id": "2026_01_DAL_PHI", "season": 2026, "week": 1,
        "season_type": "REG", "home_team": "PHI", "away_team": "DAL",
        "kickoff_at": "2026-09-10T22:00:00Z",
    }
    slot = candidate._slot_for_moneyline(game, candidate.moneyline.WINDOWS[1])
    first = repository.acquire_lease(
        slot, owner="worker-one", now=NOW - timedelta(minutes=6),
        ttl=timedelta(minutes=5),
    )
    payload = [{
        "id": "provider-event", "home_team": "Philadelphia Eagles",
        "away_team": "Dallas Cowboys",
        "bookmakers": [
            {
                "key": key, "last_update": "2026-09-10T15:55:00Z",
                "markets": [{
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Philadelphia Eagles", "price": -120 - index},
                        {"name": "Dallas Cowboys", "price": 110 + index},
                    ],
                }],
            }
            for index, key in enumerate(("betmgm", "fanduel", "draftkings"))
        ],
    }]
    source = _raw(first.slot_id, payload=payload)
    repository.checkpoint_raw((first,), source)
    counters = {
        "success": 0, "failed": 0, "missed": 0, "post_kickoff": 0,
        "existing": 0, "contended": 0, "provider_calls": 0,
    }
    recovered = candidate._prepare_lane_slots(
        repository, (game,), now=NOW, owner="worker-two",
        lane="MONEYLINE", counters=counters,
    )
    monkeypatch.setattr(
        candidate.game_day,
        "fetch_live_moneyline_payload",
        lambda: pytest.fail("RAW_CAPTURED recovery must not refetch"),
    )
    candidate._collect_moneyline(repository, recovered, now=NOW, counters=counters)
    assert counters["provider_calls"] == 0
    assert counters["success"] == 1
    assert repository.inspect_slot(first.slot_id)["state"] == "TERMINAL_SUCCESS"


def test_atomic_success_linkage_idempotency_and_terminal_immutability(
    repository: FirestoreEvidenceRepository,
) -> None:
    token = repository.acquire_lease(
        _slot(), owner="worker", now=NOW, ttl=timedelta(minutes=5)
    )
    source = _raw(token.slot_id)
    repository.checkpoint_raw((token,), source)
    observation = _identified({"value": 1}, "observation_id")
    attempt = _attempt(
        result="SUCCESS", reason="SUCCESS",
        observation_id=str(observation["observation_id"]),
    )
    repository.commit_success(
        token,
        raw_response_id=source["raw_response_id"],
        observation=observation,
        attempt=attempt,
    )
    repository.commit_success(
        token,
        raw_response_id=source["raw_response_id"],
        observation=observation,
        attempt=attempt,
    )
    stored = repository.inspect_slot(token.slot_id)
    assert stored["state"] == "TERMINAL_SUCCESS"
    assert stored["observation_id"] == observation["observation_id"]
    assert stored["attempt_id"] == attempt["attempt_id"]
    assert repository.enumerate_evidence("moneyline_observations") == (observation,)
    assert repository.enumerate_evidence("moneyline_attempts") == (attempt,)
    with pytest.raises(LeaseUnavailableError):
        repository.acquire_lease(
            _slot(), owner="other", now=NOW, ttl=timedelta(minutes=5)
        )


def test_atomic_failed_or_missed_attempt_has_no_observation(
    repository: FirestoreEvidenceRepository,
) -> None:
    token = repository.acquire_lease(
        _slot(), owner="worker", now=NOW, ttl=timedelta(minutes=5)
    )
    attempt = _attempt(result="SKIPPED_OUTSIDE_WINDOW", reason="MISSED_WINDOW")
    repository.commit_terminal_attempt(token, attempt=attempt)
    repository.commit_terminal_attempt(token, attempt=attempt)
    stored = repository.inspect_slot(token.slot_id)
    assert stored["state"] == "TERMINAL_FAILED_OR_MISSED"
    assert stored["attempt_id"] == attempt["attempt_id"]
    assert stored["observation_id"] is None
    assert repository.enumerate_evidence("moneyline_observations") == ()
    assert repository.enumerate_evidence("moneyline_attempts") == (attempt,)


@pytest.mark.parametrize("kind", ("raw", "observation", "attempt"))
def test_conflicting_immutable_documents_fail_closed(
    repository: FirestoreEvidenceRepository, kind: str
) -> None:
    token = repository.acquire_lease(
        _slot(), owner="worker", now=NOW, ttl=timedelta(minutes=5)
    )
    source = _raw(token.slot_id)
    if kind == "raw":
        repository._collection("raw_provider_responses").document(
            source["raw_response_id"]
        ).set({"conflict": True})
        with pytest.raises(ImmutableConflictError):
            repository.checkpoint_raw((token,), source)
        return

    repository.checkpoint_raw((token,), source)
    observation = _identified({"value": 1}, "observation_id")
    attempt = _attempt(
        result="SUCCESS", reason="SUCCESS",
        observation_id=str(observation["observation_id"]),
    )
    collection = "moneyline_observations" if kind == "observation" else "moneyline_attempts"
    identity = observation["observation_id"] if kind == "observation" else attempt["attempt_id"]
    repository._collection(collection).document(str(identity)).set({"conflict": True})
    with pytest.raises(ImmutableConflictError):
        repository.commit_success(
            token,
            raw_response_id=source["raw_response_id"],
            observation=observation,
            attempt=attempt,
        )
    assert repository.inspect_slot(token.slot_id)["state"] == "RAW_CAPTURED"


def test_malformed_raw_document_is_rejected(
    repository: FirestoreEvidenceRepository,
) -> None:
    repository._collection("raw_provider_responses").document("malformed").set(
        {"classification": CLASSIFICATION, "payload": []}
    )
    with pytest.raises(CloudEvidenceError, match="identity"):
        repository.get_raw_response("malformed")


def test_namespace_isolation_and_candidate_only_status(
    client: firestore.Client,
) -> None:
    first = FirestoreEvidenceRepository(client, namespace="step91x2a_one_" + uuid.uuid4().hex)
    second = FirestoreEvidenceRepository(client, namespace="step91x2a_two_" + uuid.uuid4().hex)
    first.acquire_lease(_slot(), owner="one", now=NOW, ttl=timedelta(minutes=5))
    assert second.inspect_slot(str(_slot()["slot_id"])) is None
    assert CLASSIFICATION == "NON_PROSPECTIVE_CLOUD_CANDIDATE"
    assert not hasattr(first, "promote_authority")


def test_gridiron_size_guard_precedes_firestore_write(
    repository: FirestoreEvidenceRepository,
) -> None:
    token = repository.acquire_lease(
        _slot(), owner="worker", now=NOW, ttl=timedelta(minutes=5)
    )
    near = _raw(token.slot_id, payload={"data": "x" * 850_000})
    repository.checkpoint_raw((token,), near)
    assert repository.get_raw_response(near["raw_response_id"]) == near

    other_slot = _slot("2026_01_KC_LAC")
    other = repository.acquire_lease(
        other_slot, owner="worker", now=NOW, ttl=timedelta(minutes=5)
    )
    with pytest.raises(CloudEvidenceError, match="chunking"):
        _raw(other.slot_id, payload={"data": "x" * 900_000})
    assert repository.inspect_slot(other.slot_id)["state"] == "LEASED"
    assert len(repository.enumerate_evidence("moneyline_observations")) == 0


def test_concurrent_acquisition_has_one_winner(
    repository: FirestoreEvidenceRepository,
) -> None:
    barrier = threading.Barrier(4)

    def compete(index: int) -> str:
        barrier.wait()
        time.sleep(index * 0.1)
        try:
            repository.acquire_lease(
                _slot(), owner=f"worker-{index}", now=NOW, ttl=timedelta(minutes=5)
            )
            return "won"
        except LeaseUnavailableError:
            return "lost"

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(compete, range(4)))
    assert results.count("won") == 1
    assert results.count("lost") == 3


def test_official_transaction_callbacks_retry_and_fail_closed_on_forced_contention(
    client: firestore.Client,
) -> None:
    reference = client.collection("step91x2a_retry_" + uuid.uuid4().hex).document("counter")
    reference.set({"value": 0})
    barrier = threading.Barrier(2)
    callback_counts = [0, 0]

    def contend(index: int) -> str:
        transaction = client.transaction(max_attempts=2)

        @transactional
        def apply(tx: Any) -> None:
            callback_counts[index] += 1
            value = reference.get(transaction=tx).get("value")
            if callback_counts[index] == 1:
                barrier.wait()
            tx.update(reference, {"value": value + 1})

        try:
            apply(transaction)
            return "committed"
        except ValueError:
            return "retry_exhausted"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(contend, range(2)))
    assert "retry_exhausted" in outcomes
    assert sum(callback_counts) >= 3
    assert reference.get().get("value") in {0, 1}
