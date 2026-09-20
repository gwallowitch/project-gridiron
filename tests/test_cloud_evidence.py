from __future__ import annotations

import hashlib
import http.client
import importlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from gridiron.market.closing_settlement import closing_line_from_history
from gridiron.market.cloud_evidence import (
    CloudEvidenceError,
    ImmutableConflictError,
    InMemoryEvidenceRepository,
    LeaseUnavailableError,
    StaleLeaseError,
    build_raw_response,
    build_slot,
    export_jsonl_generation,
    logical_slot_id,
    validate_raw_response,
)
from gridiron.market.collection_attempts import build_collection_attempt
from gridiron.market.operational_history import canonical_json
from scripts import gridiron_cloud_candidate as candidate
from scripts.gridiron_collection_health import audit_collection_health

NOW = datetime(2026, 9, 10, 16, tzinfo=UTC)


def slot(game_id: str = "2026_01_DAL_PHI") -> dict[str, object]:
    return build_slot(
        game_id=game_id,
        market_type="MONEYLINE",
        target_label="T6H",
        kickoff_at="2026-09-10T22:00:00Z",
        target_minutes=360,
        lower_bound_minutes=330,
        upper_bound_minutes=390,
    )


def raw(*slot_ids: str) -> dict[str, object]:
    return build_raw_response(
        provider="the-odds-api",
        lane="MONEYLINE",
        product="h2h-us-three-book",
        requested_books=("draftkings", "fanduel", "betmgm"),
        fetched_at=NOW,
        payload=[{"id": "provider-event", "bookmakers": []}],
        slot_ids=slot_ids,
        parser_version="step91q-v1",
    )


def identified(base: dict[str, object], field: str) -> dict[str, object]:
    return {
        **base,
        field: hashlib.sha256(canonical_json(base).encode()).hexdigest(),
    }


def success_attempt(observation_id: str) -> dict[str, object]:
    return build_collection_attempt(
        game_id="2026_01_DAL_PHI",
        collection_target="T6H",
        target_minutes_to_kickoff=360,
        kickoff_at="2026-09-10T22:00:00Z",
        attempted_at=NOW,
        result="SUCCESS",
        reason_code="SUCCESS",
        observation_id=observation_id,
    )


def test_slot_identity_is_exact_and_deterministic() -> None:
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
    assert slot()["slot_id"] == expected


def test_lease_contention_takeover_and_stale_owner_rejection() -> None:
    repository = InMemoryEvidenceRepository()
    original = repository.acquire_lease(slot(), owner="one", now=NOW, ttl=timedelta(minutes=5))
    with pytest.raises(LeaseUnavailableError):
        repository.acquire_lease(slot(), owner="two", now=NOW, ttl=timedelta(minutes=5))
    takeover = repository.acquire_lease(
        slot(), owner="two", now=NOW + timedelta(minutes=6), ttl=timedelta(minutes=5)
    )
    assert takeover.epoch == original.epoch + 1
    with pytest.raises(StaleLeaseError):
        repository.checkpoint_raw((original,), raw(original.slot_id))


def test_raw_response_is_sanitized_hashed_and_shared() -> None:
    first = slot()
    second = slot("2026_01_KC_LAC")
    record = raw(str(first["slot_id"]), str(second["slot_id"]))
    validate_raw_response(record)
    assert record["slot_ids"] == sorted((first["slot_id"], second["slot_id"]))
    assert "api" not in canonical_json(record).lower().replace("the-odds-api", "")
    corrupt = dict(record)
    corrupt["payload"] = []
    with pytest.raises(CloudEvidenceError, match="identity|corrupt"):
        validate_raw_response(corrupt)


@pytest.mark.parametrize(
    "payload",
    [
        {"apiKey": "secret"},
        {"Authorization": "Bearer secret"},
        {"url": "https://example.test/?apiKey=secret"},
    ],
)
def test_raw_response_rejects_secret_material(payload: object) -> None:
    with pytest.raises(CloudEvidenceError, match="secret|credential"):
        build_raw_response(
            provider="provider", lane="MONEYLINE", product="h2h",
            requested_books=("draftkings",), fetched_at=NOW, payload=payload,
            slot_ids=(str(slot()["slot_id"]),), parser_version="v1",
        )


def test_raw_response_fails_closed_instead_of_truncating_large_payload() -> None:
    with pytest.raises(CloudEvidenceError, match="chunking"):
        build_raw_response(
            provider="provider", lane="MONEYLINE", product="h2h",
            requested_books=("draftkings",), fetched_at=NOW,
            payload={"data": "x" * 900_000},
            slot_ids=(str(slot()["slot_id"]),), parser_version="v1",
        )


def test_atomic_success_commit_duplicate_and_conflict() -> None:
    repository = InMemoryEvidenceRepository()
    lease = repository.acquire_lease(slot(), owner="one", now=NOW, ttl=timedelta(minutes=5))
    source = raw(lease.slot_id)
    repository.checkpoint_raw((lease,), source)
    observation = identified({"value": 1}, "observation_id")
    attempt = success_attempt(str(observation["observation_id"]))
    repository.commit_success(
        lease, raw_response_id=str(source["raw_response_id"]),
        observation=observation, attempt=attempt,
    )
    repository.commit_success(
        lease, raw_response_id=str(source["raw_response_id"]),
        observation=observation, attempt=attempt,
    )
    assert repository.inspect_slot(lease.slot_id)["state"] == "TERMINAL_SUCCESS"
    conflict = identified({"value": 2}, "observation_id")
    with pytest.raises(ImmutableConflictError):
        repository.commit_success(
            lease, raw_response_id=str(source["raw_response_id"]),
            observation=conflict, attempt=attempt,
        )
    with pytest.raises(LeaseUnavailableError):
        repository.acquire_lease(slot(), owner="two", now=NOW, ttl=timedelta(minutes=5))


def test_raw_captured_takeover_replays_without_rebinding() -> None:
    repository = InMemoryEvidenceRepository()
    original = repository.acquire_lease(slot(), owner="one", now=NOW, ttl=timedelta(minutes=5))
    source = raw(original.slot_id)
    repository.checkpoint_raw((original,), source)
    takeover = repository.acquire_lease(
        slot(), owner="two", now=NOW + timedelta(minutes=6), ttl=timedelta(minutes=5)
    )
    retained = repository.inspect_slot(takeover.slot_id)
    assert retained["state"] == "RAW_CAPTURED"
    assert retained["raw_response_id"] == source["raw_response_id"]
    assert repository.get_raw_response(str(source["raw_response_id"])) == source
    with pytest.raises(StaleLeaseError):
        repository.commit_terminal_attempt(
            original,
            attempt=build_collection_attempt(
                game_id="2026_01_DAL_PHI", collection_target="T6H",
                target_minutes_to_kickoff=360,
                kickoff_at="2026-09-10T22:00:00Z", attempted_at=NOW,
                result="FAILED", reason_code="ODDS_PROVIDER_ERROR",
            ),
        )


def test_terminal_missed_attempt_is_immutable() -> None:
    repository = InMemoryEvidenceRepository()
    lease = repository.acquire_lease(slot(), owner="one", now=NOW, ttl=timedelta(minutes=5))
    attempt = build_collection_attempt(
        game_id="2026_01_DAL_PHI", collection_target="T6H",
        target_minutes_to_kickoff=360, kickoff_at="2026-09-10T22:00:00Z",
        attempted_at=NOW, result="SKIPPED_OUTSIDE_WINDOW", reason_code="MISSED_WINDOW",
    )
    repository.commit_terminal_attempt(lease, attempt=attempt)
    repository.commit_terminal_attempt(lease, attempt=attempt)
    assert repository.inspect_slot(lease.slot_id)["terminal_classification"] == "SKIPPED_OUTSIDE_WINDOW"
    with pytest.raises(LeaseUnavailableError):
        repository.acquire_lease(slot(), owner="again", now=NOW, ttl=timedelta(minutes=5))


def test_exporter_is_deterministic_and_preserves_generations(tmp_path: Path) -> None:
    repository = InMemoryEvidenceRepository()
    first = export_jsonl_generation(repository, cache_root=tmp_path, generation_id="g1")
    second = export_jsonl_generation(repository, cache_root=tmp_path, generation_id="g2")
    assert first.is_dir() and second.is_dir()
    assert (tmp_path / "CURRENT").read_text() == "g2\n"
    assert {path.name for path in first.iterdir()} == {
        "market_history_v1.jsonl", "collection_attempts_v1.jsonl",
        "totals_history_v1.jsonl", "totals_collection_attempts_v1.jsonl",
    }
    assert all(path.read_bytes() == b"" for path in first.iterdir())


def test_exporter_rejects_corrupt_cloud_identity(tmp_path: Path) -> None:
    repository = InMemoryEvidenceRepository()
    repository.collections["moneyline_observations"]["wrong"] = {
        "observation_id": "wrong"
    }
    with pytest.raises(CloudEvidenceError, match="observation_id"):
        export_jsonl_generation(repository, cache_root=tmp_path, generation_id="bad")
    assert not (tmp_path / "CURRENT").exists()


def test_post_kickoff_candidate_performs_no_fetch_or_backfill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schedule = tmp_path / "schedule.json"
    schedule.write_text(
        json.dumps(
            [{
                "game_id": "2026_01_DAL_PHI", "season": 2026, "week": 1,
                "season_type": "REG", "home_team": "PHI", "away_team": "DAL",
                "kickoff_at": "2026-09-10T15:00:00Z",
            }]
        )
    )
    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "test-only")
    monkeypatch.setattr(
        candidate.game_day, "fetch_live_moneyline_payload",
        lambda: pytest.fail("provider fetch must not occur"),
    )
    monkeypatch.setattr(
        candidate.totals, "fetch_live_totals_payload",
        lambda: pytest.fail("provider fetch must not occur"),
    )
    repository = InMemoryEvidenceRepository()
    result = candidate.run_cloud_candidate(
        repository, now=NOW, owner="test", schedule_path=schedule
    )
    assert result["post_kickoff"] == 2
    assert repository.enumerate_slots() == ()


def test_far_future_games_perform_no_firestore_reads_or_provider_fetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schedule = tmp_path / "schedule.json"
    schedule.write_text(
        json.dumps(
            [{
                "game_id": "2026_02_NYG_DAL", "season": 2026, "week": 2,
                "season_type": "REG", "home_team": "DAL", "away_team": "NYG",
                "kickoff_at": "2026-09-17T22:00:00Z",
            }]
        )
    )
    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "test-only")
    monkeypatch.setattr(
        candidate.game_day, "fetch_live_moneyline_payload",
        lambda: pytest.fail("provider fetch must not occur"),
    )
    monkeypatch.setattr(
        candidate.totals, "fetch_live_totals_payload",
        lambda: pytest.fail("provider fetch must not occur"),
    )

    class NoReadRepository(InMemoryEvidenceRepository):
        def inspect_slot(self, slot_id: str) -> dict[str, object] | None:
            pytest.fail(f"far-future slot must not be read: {slot_id}")

    repository = NoReadRepository()
    result = candidate.run_cloud_candidate(
        repository, now=NOW, owner="test", schedule_path=schedule
    )
    assert result["provider_calls"] == 0
    assert repository.enumerate_slots() == ()


def test_candidate_requires_api_key_before_any_state_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GRIDIRON_ODDS_API_KEY", raising=False)
    repository = InMemoryEvidenceRepository()
    with pytest.raises(CloudEvidenceError, match="GRIDIRON_ODDS_API_KEY"):
        candidate.run_cloud_candidate(
            repository, now=NOW, owner="test", schedule_path=tmp_path / "unused"
        )
    assert repository.enumerate_slots() == ()


def test_entrypoint_rejects_malformed_key_before_firestore_or_external_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "TEST\nKEY")
    monkeypatch.setattr(
        candidate.FirestoreEvidenceRepository,
        "from_default_client",
        lambda: pytest.fail("Firestore client must not be created"),
    )
    monkeypatch.setattr(
        candidate.game_day.nfl,
        "load_pbp",
        lambda _season: pytest.fail("nflverse must not be loaded"),
    )
    monkeypatch.setattr(
        candidate.game_day,
        "fetch_live_moneyline_payload",
        lambda: pytest.fail("moneyline provider must not be called"),
    )
    monkeypatch.setattr(
        candidate.totals,
        "fetch_live_totals_payload",
        lambda: pytest.fail("totals provider must not be called"),
    )
    body, status = candidate.collect_candidate(object())
    assert status == 500
    assert body["status"] == "FAILED_CLOSED"
    assert body["error_type"] == "GameDayInputError"


def test_invalid_url_cannot_create_accepted_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schedule = tmp_path / "schedule.json"
    schedule.write_text(
        json.dumps(
            [{
                "game_id": "2026_01_DAL_PHI", "season": 2026, "week": 1,
                "season_type": "REG", "home_team": "PHI", "away_team": "DAL",
                "kickoff_at": "2026-09-10T19:00:00Z",
            }]
        )
    )
    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "TEST_KEY")
    monkeypatch.setattr(
        candidate.game_day,
        "fetch_live_moneyline_payload",
        lambda: (_ for _ in ()).throw(http.client.InvalidURL("synthetic")),
    )
    repository = InMemoryEvidenceRepository()
    with pytest.raises(http.client.InvalidURL, match="synthetic"):
        candidate.run_cloud_candidate(
            repository, now=NOW, owner="test", schedule_path=schedule
        )
    assert repository.raw_responses == {}
    assert repository.collections["moneyline_observations"] == {}
    assert repository.collections["totals_observations"] == {}


def _event(home: str, away: str, event_id: str, *, totals: bool) -> dict[str, object]:
    books = []
    for index, key in enumerate(("betmgm", "fanduel", "draftkings")):
        if totals:
            outcomes = [
                {"name": "Over", "price": -110 + index, "point": 47.5},
                {"name": "Under", "price": -110 - index, "point": 47.5},
            ]
            market_key = "totals"
        else:
            outcomes = [
                {"name": home, "price": -120 - index},
                {"name": away, "price": 110 + index},
            ]
            market_key = "h2h"
        books.append(
            {
                "key": key,
                "last_update": "2026-09-10T15:55:00Z",
                "markets": [{"key": market_key, "outcomes": outcomes}],
            }
        )
    return {
        "id": event_id,
        "home_team": home,
        "away_team": away,
        "bookmakers": books,
    }


def test_candidate_reuses_one_payload_per_lane_and_exports_for_existing_consumers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    games = [
        {
            "game_id": "2026_01_DAL_PHI", "season": 2026, "week": 1,
            "season_type": "REG", "home_team": "PHI", "away_team": "DAL",
            "kickoff_at": "2026-09-10T22:00:00Z",
        },
        {
            "game_id": "2026_01_KC_LAC", "season": 2026, "week": 1,
            "season_type": "REG", "home_team": "LAC", "away_team": "KC",
            "kickoff_at": "2026-09-10T22:00:00Z",
        },
    ]
    schedule = tmp_path / "schedule.json"
    schedule.write_text(json.dumps(games))
    money_payload = [
        _event("Philadelphia Eagles", "Dallas Cowboys", "one", totals=False),
        _event("Los Angeles Chargers", "Kansas City Chiefs", "two", totals=False),
    ]
    totals_payload = [
        _event("Philadelphia Eagles", "Dallas Cowboys", "one", totals=True),
        _event("Los Angeles Chargers", "Kansas City Chiefs", "two", totals=True),
    ]
    calls = {"moneyline": 0, "totals": 0}

    def money_fetch() -> object:
        calls["moneyline"] += 1
        return money_payload

    def totals_fetch() -> object:
        calls["totals"] += 1
        return totals_payload

    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "test-only")
    monkeypatch.setattr(candidate.game_day, "fetch_live_moneyline_payload", money_fetch)
    monkeypatch.setattr(candidate.totals, "fetch_live_totals_payload", totals_fetch)
    repository = InMemoryEvidenceRepository()
    result = candidate.run_cloud_candidate(
        repository, now=NOW, owner="test", schedule_path=schedule
    )
    assert calls == {"moneyline": 1, "totals": 1}
    assert result["success"] == 4
    assert result["missed"] == 4
    assert result["authority"] == "CANDIDATE_SHADOW_ONLY"

    generation = export_jsonl_generation(
        repository, cache_root=tmp_path / "cache", generation_id="g1"
    )
    report = audit_collection_health(
        as_of=NOW,
        schedule_path=schedule,
        moneyline_history_path=generation / "market_history_v1.jsonl",
        moneyline_attempt_path=generation / "collection_attempts_v1.jsonl",
        totals_history_path=generation / "totals_history_v1.jsonl",
        totals_attempt_path=generation / "totals_collection_attempts_v1.jsonl",
        hours=24.0,
    )
    assert report["classification"] == "READ_ONLY_NON_PROSPECTIVE_COLLECTION_HEALTH"
    assert closing_line_from_history(
        generation / "market_history_v1.jsonl", "2026_01_DAL_PHI"
    )["game_id"] == "2026_01_DAL_PHI"


def test_local_modules_import_without_google_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = __import__

    def guarded(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("google.cloud"):
            raise AssertionError("local import attempted to load Google package")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", guarded)
    importlib.reload(importlib.import_module("gridiron.market.operational_repository"))
    importlib.reload(importlib.import_module("scripts.gridiron_market_collector"))
    importlib.reload(importlib.import_module("scripts.gridiron_totals_collector"))
