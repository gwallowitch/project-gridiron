from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from gridiron.market.prospective_integrity import (
    ProspectiveIntegrityError,
    append_chain_event,
    audit_manifest,
    canonical_game_id,
    capture_window_status,
    edge_trim_order,
    export_anchor,
    market_side,
    probability_metric_population,
    raw_sha256,
    read_chain,
    record_capture_attempt,
    record_status,
    register_scheduled_game,
)
from gridiron.market.prospective_ledger import CANDIDATE_ID, CONSENSUS_BOOKS


def snapshot() -> dict[str, object]:
    return {"schema_version": 1, "provider": "fixture", "captured_at": "2026-09-13T16:00:00Z", "game": {"game_id": "2026_01_BUF_NYJ", "season": 2026, "season_type": "REG", "week": 1, "kickoff_at": "2026-09-13T17:00:00Z", "home_team": "NYJ", "away_team": "BUF"}, "def_epa": None, "offers": [{"book": book, "market": "moneyline", "home_team": "NYJ", "away_team": "BUF", "home_odds": 120, "away_odds": -140, "observed_at": "2026-09-13T15:55:00Z"} for book in CONSENSUS_BOOKS]}


def test_manifest_denominator_duplicate_and_aliases(tmp_path: Path) -> None:
    chain = tmp_path / "manifest.jsonl"
    event = register_scheduled_game(chain, season=2026, week=1, away_team="BUF", home_team="NYJ", kickoff_at="2026-09-13T17:00:00Z", provider_ids=["p1"])
    assert event["status"] == "scheduled"
    with pytest.raises(ProspectiveIntegrityError, match="duplicate"):
        register_scheduled_game(chain, season=2026, week=1, away_team="BUF", home_team="NYJ", kickoff_at="2026-09-13T17:00:00Z")


def test_capture_window_is_deterministic() -> None:
    kickoff = datetime(2026, 9, 13, 17, tzinfo=UTC)
    assert capture_window_status(datetime(2026, 9, 13, 16, tzinfo=UTC), kickoff) == "IN_WINDOW"
    assert capture_window_status(datetime(2026, 9, 13, 16, 30, tzinfo=UTC), kickoff) == "OUTSIDE_WINDOW"


def test_raw_hash_receipt_and_accepted_capture(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(snapshot()), encoding="utf-8")
    event = record_capture_attempt(tmp_path / "manifest.jsonl", raw, tmp_path / "raw", receipt_at=datetime(2026, 9, 13, 16, tzinfo=UTC))
    assert event["status"] == "accepted"
    assert event["receipt_at"] == "2026-09-13T16:00:00Z"
    assert event["raw_sha256"] == raw_sha256(raw.read_bytes())
    assert event["provider_observed_at"] != [event["receipt_at"]]


def test_stale_and_missing_market_are_retained_rejections(tmp_path: Path) -> None:
    for name, mutate, reason in (("stale", lambda r: [o.update(observed_at="2026-09-13T15:40:00Z") for o in r["offers"]], "STALE_INPUT"), ("missing", lambda r: r["offers"].pop(), "NO_VALID_CONSENSUS")):
        value = snapshot(); mutate(value)
        raw = tmp_path / f"{name}.json"; raw.write_text(json.dumps(value), encoding="utf-8")
        event = record_capture_attempt(tmp_path / f"{name}.jsonl", raw, tmp_path / "raw", receipt_at=datetime(2026, 9, 13, 16, tzinfo=UTC), reason_code=reason)
        assert event["status"] == "rejected" and event["reason_code"] == reason


def test_hash_chain_detects_tampering_reordering_and_deletion_anchor(tmp_path: Path) -> None:
    chain = tmp_path / "manifest.jsonl"
    append_chain_event(chain, {"event_type": "A"}); append_chain_event(chain, {"event_type": "B"})
    assert export_anchor(chain)["events"] == 2
    events = list(read_chain(chain)); events[0]["event_type"] = "X"
    chain.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    with pytest.raises(ProspectiveIntegrityError): read_chain(chain)


def test_statuses_postponed_cancelled_and_reason_codes(tmp_path: Path) -> None:
    chain = tmp_path / "manifest.jsonl"
    game = canonical_game_id(2026, 1, "BUF", "NYJ")
    record_status(chain, game_id=game, status="postponed", reason_code="GAME_POSTPONED", recorded_at="2026-09-13T12:00:00Z")
    event = record_status(chain, game_id=game, status="cancelled", reason_code="GAME_CANCELLED", recorded_at="2026-09-14T12:00:00Z")
    assert event["status"] == "cancelled"


def test_settlement_deadline_exposes_missing_settlement(tmp_path: Path) -> None:
    chain = tmp_path / "manifest.jsonl"; ledger = tmp_path / "ledger.jsonl"
    register_scheduled_game(chain, season=2026, week=1, away_team="BUF", home_team="NYJ", kickoff_at="2026-09-13T17:00:00Z")
    record_status(chain, game_id="2026_01_BUF_NYJ", status="unavailable", reason_code="MARKET_UNAVAILABLE", recorded_at="2026-09-13T16:00:00Z")
    report = audit_manifest(chain, ledger, as_of="2026-09-20T00:00:00Z")
    assert report["overdue_settlements"] == [] and report["complete_season"] is True


def test_edge_ties_are_outcome_blind_and_deterministic() -> None:
    rows = [{"is_bet": True, "result": "HOME", "edge": 0.1, "observation_id": value} for value in ("b", "a", "c")]
    assert [r["observation_id"] for r in edge_trim_order(rows, 0.34)] == ["b", "c"]


@pytest.mark.parametrize(("probability", "label"), [(0.44, "UNDERDOG"), (0.45, "BALANCED"), (0.55, "BALANCED"), (0.56, "FAVORITE")])
def test_balanced_market_definition(probability: float, label: str) -> None:
    assert market_side(probability) == label


def test_probability_metrics_include_nonbets_but_not_pushes() -> None:
    rows = [{"result": "HOME", "is_bet": False}, {"result": "PUSH", "is_bet": True}, {"result": None, "is_bet": True}]
    assert probability_metric_population(rows) == [rows[0]]


def test_candidate_identity_and_serialization_are_frozen(tmp_path: Path) -> None:
    assert CANDIDATE_ID == "market-plus-def-epa-capped-0425-v1"
    chain = tmp_path / "manifest.jsonl"; append_chain_event(chain, {"event_type": "FIXTURE"})
    assert read_chain(chain) == read_chain(chain)
