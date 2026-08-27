from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from gridiron.market.prospective_integrity import read_chain, record_capture_attempt
from gridiron.market.prospective_ledger import (
    CONSENSUS_BOOKS,
    read_ledger,
    validate_ledger,
)
from gridiron.market.prospective_operations import (
    DRY_RUN_EVIDENCE,
    FROZEN_PROTOCOL,
    ProspectiveOperationsError,
    assert_frozen_protocol,
    capture_game,
    dry_run,
    game_day_checklist,
    initialize_manifest,
    operational_summary,
    record_game_status,
    settle_game,
)

GAME_ID = "2026_01_BUF_NYJ"
KICKOFF = "2026-09-13T17:00:00Z"
RECEIPT = "2026-09-13T16:00:00Z"


def schedule(
    *, week: int = 1, provider_ids: list[str] | None = None
) -> list[dict[str, object]]:
    return [
        {
            "game_id": f"2026_{week:02d}_BUF_NYJ",
            "season": 2026,
            "season_type": "REG",
            "week": week,
            "kickoff_at": KICKOFF,
            "home_team": "NYJ",
            "away_team": "BUF",
            "provider_ids": provider_ids or ["provider-1"],
        }
    ]


def snapshot(*, week: int = 1, def_epa: float | None = None) -> dict[str, object]:
    return {
        "schema_version": 1,
        "provider": "fixture",
        "captured_at": RECEIPT,
        "game": {
            "game_id": f"2026_{week:02d}_BUF_NYJ",
            "season": 2026,
            "season_type": "REG",
            "week": week,
            "kickoff_at": KICKOFF,
            "home_team": "NYJ",
            "away_team": "BUF",
        },
        "def_epa": def_epa,
        "offers": [
            {
                "book": book,
                "market": "moneyline",
                "home_team": "NYJ",
                "away_team": "BUF",
                "home_odds": 120,
                "away_odds": -140,
                "observed_at": "2026-09-13T15:55:00Z",
            }
            for book in CONSENSUS_BOOKS
        ],
    }


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def initialized(tmp_path: Path, *, week: int = 1) -> tuple[Path, Path, Path, Path]:
    manifest = tmp_path / "manifest.jsonl"
    ledger = tmp_path / "real-ledger.jsonl"
    raw = write_json(
        tmp_path / "raw.json", snapshot(week=week, def_epa=None if week == 1 else 0.1)
    )
    initialize_manifest(
        write_json(tmp_path / "schedule.json", schedule(week=week)), manifest
    )
    return manifest, ledger, raw, tmp_path / "raw-artifacts"


def official_result(tmp_path: Path) -> Path:
    return write_json(tmp_path / "official-result.json", {"result": "HOME"})


def test_clean_initialization_and_idempotent_update(tmp_path: Path) -> None:
    schedule_path = write_json(tmp_path / "schedule.json", schedule())
    manifest = tmp_path / "manifest.jsonl"
    assert initialize_manifest(schedule_path, manifest) == {
        "classification": "REAL_PROSPECTIVE_EVIDENCE",
        "expected": 1,
        "added": 1,
    }
    assert initialize_manifest(schedule_path, manifest)["added"] == 0
    assert len(read_chain(manifest)) == 1


def test_canonical_manifest_and_duplicate_game_prevention(tmp_path: Path) -> None:
    duplicate = schedule() * 2
    with pytest.raises(ProspectiveOperationsError, match="duplicate scheduled game"):
        initialize_manifest(
            write_json(tmp_path / "schedule.json", duplicate), tmp_path / "manifest"
        )


def test_duplicate_provider_id_prevention(tmp_path: Path) -> None:
    games = schedule()
    second = dict(games[0])
    second.update(game_id="2026_01_MIA_NE", away_team="MIA", home_team="NE")
    games.append(second)
    with pytest.raises(ProspectiveOperationsError, match="duplicate provider ID"):
        initialize_manifest(
            write_json(tmp_path / "schedule.json", games), tmp_path / "manifest"
        )


def test_capture_workflow_and_week_one_def_epa(tmp_path: Path) -> None:
    manifest, ledger, raw, artifacts = initialized(tmp_path)
    result = capture_game(
        manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=RECEIPT
    )
    assert result["attempt"]["status"] == "accepted"
    assert result["decision"]["def_epa"] == 0.0
    assert len(read_ledger(ledger)) == 1
    assert Path(result["attempt"]["raw_artifact"]).exists()


def test_explicit_game_identity_and_pre_kickoff_enforced(tmp_path: Path) -> None:
    manifest, ledger, raw, artifacts = initialized(tmp_path)
    with pytest.raises(ProspectiveOperationsError, match="explicit game identity"):
        capture_game(
            manifest,
            ledger,
            raw,
            artifacts,
            game_id="2026_01_MIA_NE",
            receipt_at=RECEIPT,
        )
    with pytest.raises(ProspectiveOperationsError, match="pre-kickoff"):
        capture_game(
            manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=KICKOFF
        )


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda value: value["offers"].pop(), "NO_VALID_CONSENSUS"),
        (
            lambda value: value["offers"].__setitem__(
                6, {**value["offers"][6], "home_odds": None}
            ),
            "NO_EXECUTABLE_DRAFTKINGS_PRICE",
        ),
        (
            lambda value: [
                offer.update(observed_at="2026-09-13T15:40:00Z")
                for offer in value["offers"]
            ],
            "STALE_INPUT",
        ),
    ],
)
def test_seven_book_missing_price_and_stale_rejections(
    tmp_path: Path, mutation: object, reason: str
) -> None:
    manifest, ledger, raw, artifacts = initialized(tmp_path)
    value = snapshot()
    mutation(value)  # type: ignore[operator]
    write_json(raw, value)
    result = capture_game(
        manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=RECEIPT
    )
    assert result["decision"] is None
    assert result["attempt"]["status"] == "rejected"
    assert result["attempt"]["reason_code"] == reason
    assert not ledger.exists()


def test_draftkings_identity_is_enforced(tmp_path: Path) -> None:
    manifest, ledger, raw, artifacts = initialized(tmp_path)
    value = snapshot()
    value["offers"][-1]["book"] = "draft-kings-impostor"
    write_json(raw, value)
    result = capture_game(
        manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=RECEIPT
    )
    assert result["attempt"]["status"] == "rejected"


def test_later_week_missing_def_epa_is_rejected(tmp_path: Path) -> None:
    manifest, ledger, raw, artifacts = initialized(tmp_path, week=2)
    write_json(raw, snapshot(week=2, def_epa=None))
    result = capture_game(
        manifest,
        ledger,
        raw,
        artifacts,
        game_id="2026_02_BUF_NYJ",
        receipt_at=RECEIPT,
    )
    assert result["attempt"]["status"] == "rejected"
    assert not ledger.exists()


def test_retry_is_explicit_and_accepted_decision_is_immutable(tmp_path: Path) -> None:
    manifest, ledger, raw, artifacts = initialized(tmp_path)
    stale = snapshot()
    for offer in stale["offers"]:
        offer["observed_at"] = "2026-09-13T15:40:00Z"
    write_json(raw, stale)
    assert (
        capture_game(
            manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=RECEIPT
        )["decision"]
        is None
    )
    write_json(raw, snapshot())
    assert (
        capture_game(
            manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=RECEIPT
        )["decision"]
        is not None
    )
    with pytest.raises(ProspectiveOperationsError, match="already captured"):
        capture_game(
            manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=RECEIPT
        )
    assert (
        len(
            [
                e
                for e in read_chain(manifest)
                if e.get("event_type") == "CAPTURE_ATTEMPT"
            ]
        )
        == 2
    )


def test_interrupted_append_recovers_without_a_second_attempt(tmp_path: Path) -> None:
    manifest, ledger, raw, artifacts = initialized(tmp_path)
    record_capture_attempt(
        manifest,
        raw,
        artifacts,
        receipt_at=datetime(2026, 9, 13, 16, tzinfo=UTC),
    )
    result = capture_game(
        manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=RECEIPT
    )
    assert result["recovered_interrupted_append"] is True
    assert len(read_ledger(ledger)) == 1
    assert (
        len(
            [
                e
                for e in read_chain(manifest)
                if e.get("event_type") == "CAPTURE_ATTEMPT"
            ]
        )
        == 1
    )


@pytest.mark.parametrize("status", ["postponed", "cancelled", "unavailable"])
def test_explicit_operational_statuses(tmp_path: Path, status: str) -> None:
    manifest, _, _, _ = initialized(tmp_path)
    event = record_game_status(
        manifest, game_id=GAME_ID, status=status, recorded_at=RECEIPT
    )
    assert event["status"] == status
    assert (
        event["reason_code"].startswith("GAME_")
        or event["reason_code"] == "MARKET_UNAVAILABLE"
    )


def test_append_only_settlement_and_integrity_validation(tmp_path: Path) -> None:
    manifest, ledger, raw, artifacts = initialized(tmp_path)
    capture_game(manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=RECEIPT)
    source = official_result(tmp_path)
    settle_game(
        manifest,
        ledger,
        game_id=GAME_ID,
        result="HOME",
        final_at="2026-09-13T20:00:00Z",
        settled_at="2026-09-13T20:00:00Z",
        result_source=source,
    )
    assert len(validate_ledger(ledger).settlements) == 1
    final = next(
        event for event in read_chain(manifest) if event["event_type"] == "GAME_FINAL"
    )
    assert final["source_sha256"]
    with pytest.raises(ProspectiveOperationsError, match="duplicate settlement"):
        settle_game(
            manifest,
            ledger,
            game_id=GAME_ID,
            result="AWAY",
            final_at="2026-09-13T20:00:00Z",
            settled_at="2026-09-13T20:01:00Z",
            result_source=source,
        )


def test_settlement_requires_retained_source_and_valid_timing(tmp_path: Path) -> None:
    manifest, ledger, raw, artifacts = initialized(tmp_path)
    capture_game(manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=RECEIPT)
    with pytest.raises(ProspectiveOperationsError, match="not retained"):
        settle_game(
            manifest,
            ledger,
            game_id=GAME_ID,
            result="HOME",
            final_at="2026-09-13T20:00:00Z",
            settled_at="2026-09-13T20:00:00Z",
            result_source=tmp_path / "missing-result",
        )
    with pytest.raises(
        ProspectiveOperationsError, match="cannot precede official final"
    ):
        settle_game(
            manifest,
            ledger,
            game_id=GAME_ID,
            result="HOME",
            final_at="2026-09-13T20:00:00Z",
            settled_at="2026-09-13T19:59:00Z",
            result_source=official_result(tmp_path),
        )


def test_operational_summary_accounts_for_all_states(tmp_path: Path) -> None:
    manifest, ledger, raw, artifacts = initialized(tmp_path)
    capture_game(manifest, ledger, raw, artifacts, game_id=GAME_ID, receipt_at=RECEIPT)
    report = operational_summary(manifest, ledger, as_of="2026-09-13T16:01:00Z")
    assert report["scheduled_games"] == report["accounted_for_games"] == 1
    assert report["capture_attempts"] == report["accepted_decisions"] == 1
    assert report["missing_games"] == []
    assert report["prospective_evidence_count"] == 1


def test_dry_run_isolation_and_complete_path(tmp_path: Path) -> None:
    real_ledger = tmp_path / "real.jsonl"
    result = dry_run(tmp_path / "isolated")
    assert result["classification"] == DRY_RUN_EVIDENCE
    assert result["capture_status"] == "accepted"
    assert result["decision_recorded"] and result["settlement_recorded"]
    assert result["integrity_valid"]
    assert not real_ledger.exists()
    assert result["summary"]["classification"] == DRY_RUN_EVIDENCE


def test_dry_run_refuses_nonempty_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "not-empty"
    workspace.mkdir()
    (workspace / "real-ledger.jsonl").write_text("sacred", encoding="utf-8")
    with pytest.raises(ProspectiveOperationsError, match="must be empty"):
        dry_run(workspace)
    assert (workspace / "real-ledger.jsonl").read_text(encoding="utf-8") == "sacred"


def test_frozen_protocol_assertion_rejects_every_mismatch() -> None:
    assert_frozen_protocol(FROZEN_PROTOCOL)
    for key in FROZEN_PROTOCOL:
        changed = dict(FROZEN_PROTOCOL)
        changed[key] = "MISMATCH"
        with pytest.raises(ProspectiveOperationsError, match="mismatch"):
            assert_frozen_protocol(changed)


def test_objective_checklist_and_deterministic_serialization(tmp_path: Path) -> None:
    checklist = game_day_checklist()
    assert set(checklist) == {"before_capture", "at_capture", "after_capture"}
    first = dry_run(tmp_path / "one")
    second = dry_run(tmp_path / "two")
    for value in (first, second):
        value.pop("isolated_workspace")
        value["summary"].pop("terminal_hash")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
