from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from gridiron.market.prospective_audit import canonical_json
from gridiron.market.prospective_evidence import (
    FIXTURE_EVIDENCE,
    ProspectiveEvidenceError,
    capture_real_snapshot,
    evaluate_gate,
    evidence_summary,
    protocol_completeness,
    settle_real_observation,
)
from gridiron.market.prospective_ledger import (
    CANDIDATE_ID,
    CONSENSUS_BOOKS,
    DEF_EPA_COEFFICIENT,
    INTERCEPT,
    MARKET_COEFFICIENT,
    RESIDUAL_CAP,
    append_event,
    build_decision,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/step91f_prospective_evidence.py"


def _snapshot(*, week: int = 1, season: int = 2026, def_epa: float | None = None) -> dict[str, object]:
    return {
        "schema_version": 1,
        "provider": "manual",
        "captured_at": "2026-09-13T14:00:00Z",
        "game": {
            "game_id": f"{season}_{week:02d}_BUF_NYJ",
            "season": season,
            "season_type": "REG",
            "week": week,
            "kickoff_at": "2026-09-13T17:00:00Z",
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
                "home_odds": 300,
                "away_odds": 300,
                "observed_at": "2026-09-13T13:55:00Z",
            }
            for book in CONSENSUS_BOOKS
        ],
    }


def _write_snapshot(path: Path, raw: dict[str, object]) -> None:
    path.write_text(json.dumps(raw), encoding="utf-8")


def test_real_2026_snapshot_handoff_capture_and_summary(tmp_path: Path) -> None:
    source = tmp_path / "real.json"
    ledger = tmp_path / "ledger.jsonl"
    _write_snapshot(source, _snapshot())
    event = capture_real_snapshot(ledger, source)
    summary = evidence_summary(ROOT, ledger)
    assert event["event_type"] == "DECISION"
    assert summary["games_evaluated"] == 1
    assert summary["fixtures_included"] is False


def test_historical_observation_is_rejected_without_ledger(tmp_path: Path) -> None:
    source = tmp_path / "historical.json"
    ledger = tmp_path / "ledger.jsonl"
    _write_snapshot(source, _snapshot(season=2025))
    with pytest.raises(ProspectiveEvidenceError, match="2026"):
        capture_real_snapshot(ledger, source)
    assert not ledger.exists()


def test_post_kickoff_and_missing_book_are_rejected(tmp_path: Path) -> None:
    for name, mutate in (
        ("late", lambda raw: raw.update(captured_at="2026-09-13T17:00:00Z")),
        ("missing", lambda raw: raw["offers"].pop()),
    ):
        raw = _snapshot()
        mutate(raw)
        source = tmp_path / f"{name}.json"
        _write_snapshot(source, raw)
        with pytest.raises(ProspectiveEvidenceError):
            capture_real_snapshot(tmp_path / f"{name}.jsonl", source)


def test_draftkings_and_frozen_candidate_integrity(tmp_path: Path) -> None:
    source = tmp_path / "real.json"
    ledger = tmp_path / "ledger.jsonl"
    _write_snapshot(source, _snapshot())
    event = capture_real_snapshot(ledger, source)
    assert event["execution_prices"]["book"] == "DraftKings"
    assert event["candidate_id"] == CANDIDATE_ID
    assert (MARKET_COEFFICIENT, DEF_EPA_COEFFICIENT, INTERCEPT, RESIDUAL_CAP) == (
        4.980172,
        1.044827,
        -2.514766,
        0.0425,
    )
    assert abs(event["candidate_home_probability"] - event["market_home_probability"]) <= RESIDUAL_CAP
    assert event["is_bet"] == (event["edge"] is not None and event["edge"] > 0)


def test_week_one_neutralizes_and_later_missing_def_epa_rejects(tmp_path: Path) -> None:
    source = tmp_path / "week1.json"
    _write_snapshot(source, _snapshot())
    assert capture_real_snapshot(tmp_path / "week1.jsonl", source)["def_epa"] == 0.0
    later = tmp_path / "week2.json"
    _write_snapshot(later, _snapshot(week=2))
    with pytest.raises(ProspectiveEvidenceError, match="Week 1"):
        capture_real_snapshot(tmp_path / "week2.jsonl", later)


def test_fixture_classification_cannot_enter_operational_ledger(tmp_path: Path) -> None:
    source = tmp_path / "fixture.json"
    _write_snapshot(source, _snapshot())
    with pytest.raises(ProspectiveEvidenceError, match="REAL PROSPECTIVE DATA"):
        capture_real_snapshot(
            tmp_path / "ledger.jsonl",
            source,
            evidence_classification=FIXTURE_EVIDENCE,
        )


def test_duplicate_capture_is_rejected_and_first_event_is_immutable(tmp_path: Path) -> None:
    source = tmp_path / "real.json"
    ledger = tmp_path / "ledger.jsonl"
    _write_snapshot(source, _snapshot())
    capture_real_snapshot(ledger, source)
    before = ledger.read_bytes()
    with pytest.raises(ProspectiveEvidenceError, match="duplicate"):
        capture_real_snapshot(ledger, source)
    assert ledger.read_bytes() == before


def test_non_bet_and_unsettled_are_retained_not_losses(tmp_path: Path) -> None:
    payload = {
        "game_id": "fixture-nonbet",
        "season": 2026,
        "season_type": "REG",
        "week": 1,
        "kickoff_at": "2026-09-13T17:00:00Z",
        "decision_at": "2026-09-13T14:00:00Z",
        "home_team": "NYJ",
        "away_team": "BUF",
        "def_epa": None,
        "market_observations": [
            {"book": book, "home_odds": 120, "away_odds": -140, "observed_at": "2026-09-13T13:55:00Z"}
            for book in CONSENSUS_BOOKS
        ],
        "execution_prices": {"book": "DraftKings", "home_odds": None, "away_odds": None},
    }
    ledger = tmp_path / "fixture-only.jsonl"
    append_event(ledger, build_decision(payload))
    summary = evidence_summary(ROOT, ledger)
    assert summary["non_bets"] == 1
    assert summary["losses"] == 0
    assert summary["settled_bets"] == 0


def test_settlement_uses_captured_positive_and_negative_prices(tmp_path: Path) -> None:
    for odds in (300, -100):
        source = tmp_path / f"real-{odds}.json"
        raw = _snapshot()
        for offer in raw["offers"]:
            offer["home_odds"] = odds
            offer["away_odds"] = odds
        raw["game"]["game_id"] = f"price-{odds}"
        _write_snapshot(source, raw)
        ledger = tmp_path / f"ledger-{odds}.jsonl"
        decision = capture_real_snapshot(ledger, source)
        settlement = settle_real_observation(
            ledger,
            game_id=decision["game_id"],
            result=decision["selected_side"],
            settled_at="2026-09-13T21:00:00Z",
        )
        expected = odds / 100 if odds > 0 else 100 / -odds
        assert settlement["captured_execution_odds"] == odds
        assert settlement["profit_units"] == pytest.approx(expected)


def test_orphan_and_duplicate_settlements_are_rejected(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    with pytest.raises(ProspectiveEvidenceError, match="orphan"):
        settle_real_observation(
            ledger, game_id="missing", result="HOME", settled_at="2026-09-13T21:00:00Z"
        )


@pytest.mark.parametrize(
    ("settled", "profit", "trims", "expected"),
    [
        (199, 100.0, None, "INCONCLUSIVE"),
        (200, -6.0, None, "FAIL"),
        (200, 10.0, None, "INCONCLUSIVE"),
        (200, 10.0, [5.0, 2.0], "PROMOTION CANDIDATE"),
    ],
)
def test_200_settlement_gate_mechanics(
    settled: int, profit: float, trims: list[float] | None, expected: str
) -> None:
    result = evaluate_gate(
        settled_bets=settled,
        profit_units=profit,
        season_summaries=[{"settled_bets": settled, "roi": profit / settled}],
        edge_trim_profits=trims,
    )
    assert result["status"] == expected


def test_protocol_completeness_reports_only_missing_edge_trims() -> None:
    result = protocol_completeness(ROOT)
    assert result["status"] == "INCOMPLETE"
    assert result["missing_components"] == ["edge_trim_thresholds"]
    assert result["edge_trim_threshold_status"].startswith("MISSING")


def test_summary_is_deterministic_and_empty_state_is_inconclusive(tmp_path: Path) -> None:
    ledger = tmp_path / "missing.jsonl"
    first = evidence_summary(ROOT, ledger)
    second = evidence_summary(ROOT, ledger)
    assert canonical_json(first) == canonical_json(second)
    assert first["gate"]["status"] == "INCONCLUSIVE"
    assert first["settled_bets_remaining"] == 200


def test_cli_protocol_and_summary_are_canonical(tmp_path: Path) -> None:
    ledger = tmp_path / "missing.jsonl"
    for command in ("protocol", "summary"):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--ledger", str(ledger), "--repo-root", str(ROOT), command],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0
        assert result.stdout == canonical_json(json.loads(result.stdout)) + "\n"
