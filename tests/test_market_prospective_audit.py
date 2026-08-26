from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from gridiron.market.prospective_audit import (
    ProspectiveAuditError,
    audit_prospective_pipeline,
    canonical_json,
)
from gridiron.market.prospective_ledger import (
    CONSENSUS_BOOKS,
    LedgerError,
    build_decision,
    build_settlement,
    capture_decision,
    validate_events,
)
from gridiron.market.prospective_market_ingestion import capture_market_decision

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/step91e_prospective_audit.py"


def _snapshot(game_id: str = "2026_01_BUF_NYJ") -> dict[str, object]:
    return {
        "schema_version": 1,
        "provider": "manual",
        "captured_at": "2026-09-13T14:00:00Z",
        "game": {
            "game_id": game_id,
            "season": 2026,
            "season_type": "REG",
            "week": 1,
            "kickoff_at": "2026-09-13T17:00:00Z",
            "home_team": "NYJ",
            "away_team": "BUF",
        },
        "def_epa": None,
        "offers": [
            {
                "book": book,
                "market": "moneyline",
                "home_team": "NYJ",
                "away_team": "BUF",
                "home_odds": 300,
                "away_odds": 300,
                "observed_at": "2026-09-13T13:55:00Z",
            }
            for book in CONSENSUS_BOOKS
        ],
    }


def _payload(game_id: str, *, execution: bool = True) -> dict[str, object]:
    payload = {
        "game_id": game_id,
        "season": 2026,
        "season_type": "REG",
        "week": 1,
        "kickoff_at": "2026-09-13T17:00:00Z",
        "decision_at": "2026-09-13T14:00:00Z",
        "home_team": "NYJ",
        "away_team": "BUF",
        "def_epa": None,
        "market_observations": [
            {"book": book, "home_odds": 300, "away_odds": 300, "observed_at": "2026-09-13T13:55:00Z"}
            for book in CONSENSUS_BOOKS
        ],
    }
    if not execution:
        payload["execution_prices"] = {"book": "DraftKings", "home_odds": None, "away_odds": None}
    return payload


def test_empty_missing_ledger_is_valid_and_inconclusive(tmp_path: Path) -> None:
    report = audit_prospective_pipeline(ROOT, tmp_path / "missing.jsonl")
    assert report["pipeline_status"]["operational"] is True
    assert report["ledger"]["decisions"] == 0
    assert report["economic_pipeline"]["sample_status"] == "INCONCLUSIVE / NO PROSPECTIVE SAMPLE"
    assert report["economic_pipeline"]["roi"] is None
    assert report["decision_gate"] == "INCONCLUSIVE"


def test_ingestion_capture_settlement_and_audit_end_to_end(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    decision = capture_market_decision(ledger, _snapshot())
    settlement = build_settlement(decision, result=decision["selected_side"], settled_at="2026-09-13T21:00:00Z")
    from gridiron.market.prospective_ledger import append_event

    append_event(ledger, settlement)
    report = audit_prospective_pipeline(ROOT, ledger)
    assert report["ledger"]["decisions"] == 1
    assert report["ledger"]["settlements"] == 1
    assert report["economic_pipeline"]["settled_bets"] == 1


def test_snapshot_audit_uses_91d_without_mutating_ledger(tmp_path: Path) -> None:
    source = tmp_path / "snapshot.json"
    source.write_text(json.dumps(_snapshot()), encoding="utf-8")
    ledger = tmp_path / "ledger.jsonl"
    report = audit_prospective_pipeline(ROOT, ledger, [source])
    assert report["market_ingestion"]["snapshots_available"] == 1
    assert not ledger.exists()


def test_retained_non_bet_is_counted(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    capture_decision(ledger, _payload("nonbet", execution=False))
    report = audit_prospective_pipeline(ROOT, ledger)
    assert report["ledger"]["retained_non_bets"] == 1


def test_orphan_duplicate_and_inconsistent_events_remain_rejected() -> None:
    decision = build_decision(_payload("game"))
    settlement = build_settlement(decision, result="HOME", settled_at="2026-09-13T21:00:00Z")
    with pytest.raises(LedgerError, match="orphan"):
        validate_events([settlement])
    with pytest.raises(LedgerError, match="duplicate"):
        validate_events([decision, decision])
    with pytest.raises(LedgerError, match="inconsistent"):
        validate_events([decision, settlement | {"profit_units": 99.0}])


def test_invalid_ledger_is_an_audit_failure(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(ProspectiveAuditError, match="invalid prospective ledger"):
        audit_prospective_pipeline(ROOT, ledger)


def test_same_evidence_produces_identical_canonical_report(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    first = audit_prospective_pipeline(ROOT, ledger)
    second = audit_prospective_pipeline(ROOT, ledger)
    assert canonical_json(first) == canonical_json(second)


def test_cli_emits_canonical_json_for_empty_state(tmp_path: Path) -> None:
    ledger = tmp_path / "missing.jsonl"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger), "--repo-root", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["decision_gate"] == "INCONCLUSIVE"
    assert result.stdout == canonical_json(json.loads(result.stdout)) + "\n"


def test_operational_capacity_does_not_claim_research_evidence(tmp_path: Path) -> None:
    report = audit_prospective_pipeline(ROOT, tmp_path / "missing.jsonl")
    assert report["operational_capacity"]["supports_200_plus_settlements"] is True
    assert report["operational_capacity"]["research_evidence"] is False


def test_temporary_fixture_demonstrates_200_settlement_capacity(
    tmp_path: Path,
) -> None:
    events = []
    for index in range(200):
        decision = build_decision(_payload(f"capacity-{index:03d}"))
        settlement = build_settlement(
            decision,
            result=decision["selected_side"],
            settled_at="2026-09-13T21:00:00Z",
        )
        events.extend((decision, settlement))
    validate_events(events)
    ledger = tmp_path / "capacity-fixture.jsonl"
    ledger.write_text(
        "".join(canonical_json(event) + "\n" for event in events),
        encoding="utf-8",
    )

    report = audit_prospective_pipeline(ROOT, ledger)

    assert report["ledger"]["decisions"] == 200
    assert report["ledger"]["settlements"] == 200
    assert report["economic_pipeline"]["settled_bets"] == 200
    assert report["operational_capacity"]["research_evidence"] is False
