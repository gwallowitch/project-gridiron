from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from gridiron.market.prospective_ledger import (
    CANDIDATE_ID,
    DEF_EPA_COEFFICIENT,
    INTERCEPT,
    MARKET_COEFFICIENT,
    RESIDUAL_CAP,
)
from scripts.gridiron_operational_prediction import OPERATIONAL_IDENTITY

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gridiron_operational_prediction.py"
BOOKS = ("BetMGM", "FanDuel", "DraftKings")


def _snapshot(minutes_before: int = 720) -> dict[str, object]:
    kickoff = datetime(2026, 9, 13, 17, tzinfo=UTC)
    capture = kickoff - timedelta(minutes=minutes_before)
    observed_at = capture - timedelta(minutes=5)
    captured = capture.isoformat().replace("+00:00", "Z")
    observed = observed_at.isoformat().replace("+00:00", "Z")
    return {
        "schema_version": 1,
        "captured_at": captured,
        "game": {
            "game_id": "2026_01_BUF_NYJ",
            "kickoff_at": "2026-09-13T17:00:00Z",
            "home_team": "NYJ",
            "away_team": "BUF",
        },
        "offers": [
            {
                "book": book,
                "home_odds": 120 + index,
                "away_odds": -140 - index,
                "observed_at": observed,
            }
            for index, book in enumerate(BOOKS)
        ],
    }


def _run(
    tmp_path: Path, snapshot: object, *extra: str
) -> subprocess.CompletedProcess[str]:
    source = tmp_path / "operational.json"
    source.write_text(json.dumps(snapshot), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(source),
            "--def-epa",
            "0.2",
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(720, "720.0"), (360, "360.0"), (180, "180.0"), (60, "60.0")],
)
def test_any_pre_kickoff_time_is_accepted(
    tmp_path: Path, minutes: int, expected: str
) -> None:
    result = _run(tmp_path, _snapshot(minutes))
    assert result.returncode == 0
    assert f"Minutes to kickoff: {expected}" in result.stdout
    assert "GRIDIRON OPERATIONAL PREDICTION" in result.stdout
    assert "NON-PROSPECTIVE" in result.stdout
    assert "Decision:" in result.stdout


def test_deterministic_output_and_frozen_values_are_explicit(tmp_path: Path) -> None:
    snapshot = _snapshot(360)
    first = _run(tmp_path, snapshot)
    second = _run(tmp_path, snapshot)
    assert first.stdout == second.stdout
    assert "Market books: BetMGM + FanDuel + DraftKings" in first.stdout
    assert "THREE-BOOK OPERATIONAL CONSENSUS" in first.stdout
    assert "Caller-supplied DEF EPA: 0.2" in first.stdout
    assert "Frozen coefficients reused: YES" in first.stdout
    assert "Residual cap reused: 4.25%" in first.stdout
    assert "Formal Step 91B prospective protocol: NO" in first.stdout
    assert "Model home probability:" in first.stdout
    assert "Model away probability:" in first.stdout
    assert "Selected side:" in first.stdout
    assert "Edge:" in first.stdout
    assert "Decision:" in first.stdout
    assert "THIS RESULT DOES NOT COUNT AS FORMAL PROSPECTIVE EVIDENCE." in first.stdout
    assert OPERATIONAL_IDENTITY != CANDIDATE_ID
    assert (MARKET_COEFFICIENT, DEF_EPA_COEFFICIENT, INTERCEPT, RESIDUAL_CAP) == (
        4.980172,
        1.044827,
        -2.514766,
        0.0425,
    )


def test_no_ledger_or_evidence_is_created_or_modified(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    evidence = tmp_path / "evidence.json"
    ledger.write_bytes(b"ledger")
    evidence.write_bytes(b"evidence")
    result = _run(tmp_path, _snapshot(180))
    assert result.returncode == 0
    assert ledger.read_bytes() == b"ledger"
    assert evidence.read_bytes() == b"evidence"
    assert "No prospective ledger written." in result.stdout
    assert "No prospective evidence created." in result.stdout


def test_post_kickoff_missing_book_and_missing_def_epa_fail_cleanly(
    tmp_path: Path,
) -> None:
    post = _snapshot(60)
    post["captured_at"] = "2026-09-13T17:01:00Z"
    missing = _snapshot(60)
    missing["offers"] = missing["offers"][:-1]
    for snapshot in (post, missing):
        result = _run(tmp_path, snapshot)
        assert result.returncode == 2
        assert "error:" in result.stderr
        assert "Traceback" not in result.stderr
    source = tmp_path / "missing-def-epa.json"
    source.write_text(json.dumps(_snapshot(60)), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(source)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "--def-epa" in result.stderr
    assert "Traceback" not in result.stderr


def test_stale_prices_are_rejected_for_operational_prediction(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot(180)
    snapshot["offers"][0]["observed_at"] = "2026-09-13T12:00:00Z"

    result = _run(tmp_path, snapshot)

    assert result.returncode == 2
    assert result.stdout == ""
    assert "fresh complete market data required" in result.stderr
    assert "BetMGM:STALE_PRICE_120.0_MINUTES" in result.stderr
    assert "Traceback" not in result.stderr


def test_existing_step91d_and_exploratory_viewer_remain_separate() -> None:
    step91d = (ROOT / "scripts" / "step91d_market_ingestion.py").read_text(
        encoding="utf-8"
    )
    viewer = (ROOT / "scripts" / "step91d_three_book_exploratory.py").read_text(
        encoding="utf-8"
    )
    assert "gridiron_operational_prediction" not in step91d
    assert "gridiron_operational_prediction" not in viewer
