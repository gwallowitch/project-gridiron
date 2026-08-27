from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from gridiron.market.prospective_ledger import (
    CANDIDATE_ID,
    CONSENSUS_BOOKS,
    DEF_EPA_COEFFICIENT,
    EXECUTION_BOOK,
    INTERCEPT,
    MARKET_COEFFICIENT,
    RESIDUAL_CAP,
    LedgerError,
    build_decision,
)
from gridiron.market.prospective_market_ingestion import (
    ProspectiveMarketIngestionError,
    build_ledger_payload,
)
from gridiron.market.prospective_readiness import (
    canonical_json,
    end_to_end_readiness,
    frozen_protocol_audit,
    operator_requirements,
    readiness_report,
    recover_edge_trim_definitions,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/step91g_protocol_readiness.py"


def _snapshot(**game_updates: object) -> dict[str, object]:
    game = {
        "game_id": "2026_01_BUF_NYJ",
        "season": 2026,
        "season_type": "REG",
        "week": 1,
        "kickoff_at": "2026-09-13T17:00:00Z",
        "home_team": "NYJ",
        "away_team": "BUF",
    }
    game.update(game_updates)
    return {
        "schema_version": 1,
        "provider": "manual",
        "captured_at": "2026-09-13T14:00:00Z",
        "game": game,
        "def_epa": None,
        "offers": [
            {
                "book": book,
                "market": "moneyline",
                "home_team": "NYJ",
                "away_team": "BUF",
                "home_odds": 120,
                "away_odds": -140,
                "observed_at": "2026-09-13T13:55:00Z",
            }
            for book in CONSENSUS_BOOKS
        ],
    }


def test_frozen_identity_coefficients_cap_books_and_execution() -> None:
    audit = frozen_protocol_audit(ROOT)
    assert audit["status"] == "PASS"
    assert CANDIDATE_ID == "market-plus-def-epa-capped-0425-v1"
    assert (MARKET_COEFFICIENT, DEF_EPA_COEFFICIENT, INTERCEPT, RESIDUAL_CAP) == (
        4.980172,
        1.044827,
        -2.514766,
        0.0425,
    )
    assert CONSENSUS_BOOKS == (
        "Bet365", "SI", "Betway", "BetMGM", "FanDuel", "Caesars", "DraftKings"
    )
    assert EXECUTION_BOOK == "DraftKings"


def test_2026_boundary_and_timestamp_enforcement() -> None:
    with pytest.raises(ProspectiveMarketIngestionError, match="2026"):
        build_ledger_payload(_snapshot(season=2025))
    raw = _snapshot()
    raw["captured_at"] = raw["game"]["kickoff_at"]
    with pytest.raises(ProspectiveMarketIngestionError, match="strictly earlier"):
        build_ledger_payload(raw)


def test_week_one_and_later_def_epa_rules() -> None:
    assert build_decision(build_ledger_payload(_snapshot()))["def_epa"] == 0.0
    with pytest.raises(ProspectiveMarketIngestionError, match="Week 1"):
        build_ledger_payload(_snapshot(week=2))


def test_missing_execution_remains_non_bet() -> None:
    payload = build_ledger_payload(_snapshot())
    payload["execution_prices"] = {
        "book": "DraftKings",
        "home_odds": None,
        "away_odds": None,
    }
    event = build_decision(payload)
    assert event["is_bet"] is False
    assert event["edge"] is None


def test_edge_trim_recovery_has_exact_provenance_and_no_invention() -> None:
    result = recover_edge_trim_definitions(ROOT)
    assert result["classification"] == "AUTHORITATIVELY_RECOVERABLE_WITH_PROVENANCE_LIMITATION"
    assert [item["exclude_largest_fraction"] for item in result["definitions"]] == [0.01, 0.05, 0.10]
    assert result["definition_source"]["published_commit"].startswith("2b83303")
    assert result["fully_closed"] is False
    assert "tie" in result["unresolved_limitation"]


def test_tampered_definition_is_not_recoverable(tmp_path: Path) -> None:
    (tmp_path / "STEP90G_BUILD_PROMPT.md").write_text(
        "excluding a convenient percentile", encoding="utf-8"
    )
    result = recover_edge_trim_definitions(tmp_path)
    assert result["classification"] == "NOT_AUTHORITATIVELY_RECOVERABLE"
    assert result["definitions"] is None


def test_step91c_through_step91f_chain_is_discovered() -> None:
    result = end_to_end_readiness(ROOT)
    assert result["status"] == "PASS"
    assert all(result["stages"].values())
    assert all(result["invariants"].values())


def test_operator_requirements_are_exact_and_complete() -> None:
    requirements = operator_requirements()
    assert requirements["pre_game_snapshot"]["books"] == list(CONSENSUS_BOOKS)
    assert requirements["pre_game_snapshot"]["execution_book"] == "DraftKings"
    assert requirements["post_game_settlement"]["required"] == [
        "game_id", "result", "settled_at"
    ]


def test_readiness_is_limited_and_no_evidence_is_fabricated(tmp_path: Path) -> None:
    ledger = tmp_path / "missing.jsonl"
    report = readiness_report(ROOT, ledger)
    assert report["status"] == "READY_WITH_DOCUMENTED_LIMITATION"
    assert report["real_data_readiness"]["can_accept_first_real_observation"] is True
    assert report["current_evidence"] == {
        "classification": "REAL PROSPECTIVE DATA",
        "decisions": 0,
        "settled_bets": 0,
        "gate": "INCONCLUSIVE",
        "fixtures_included": False,
    }
    assert not ledger.exists()


def test_report_and_cli_serialization_are_deterministic(tmp_path: Path) -> None:
    ledger = tmp_path / "missing.jsonl"
    first = readiness_report(ROOT, ledger)
    second = readiness_report(ROOT, ledger)
    assert canonical_json(first) == canonical_json(second)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger), "--repo-root", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout == canonical_json(json.loads(result.stdout)) + "\n"


def test_missing_required_market_price_is_rejected() -> None:
    raw = _snapshot()
    raw["offers"][0]["home_odds"] = None
    with pytest.raises(ProspectiveMarketIngestionError, match="home_odds"):
        build_ledger_payload(raw)


def test_duplicate_decision_rejection_remains_in_step91c() -> None:
    event = build_decision(build_ledger_payload(_snapshot()))
    from gridiron.market.prospective_ledger import validate_events

    with pytest.raises(LedgerError, match="duplicate"):
        validate_events((event, event))
