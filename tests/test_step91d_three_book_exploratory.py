from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "step91d_three_book_exploratory.py"
BOOKS = ("BetMGM", "FanDuel", "DraftKings")


def _snapshot(*, captured_at: str = "2026-09-13T13:00:00Z") -> dict[str, object]:
    return {
        "schema_version": 1,
        "captured_at": captured_at,
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
                "observed_at": "2026-09-13T12:55:00Z",
            }
            for index, book in enumerate(BOOKS)
        ],
    }


def _run(tmp_path: Path, snapshot: object) -> subprocess.CompletedProcess[str]:
    source = tmp_path / "exploratory.json"
    source.write_text(json.dumps(snapshot), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(source)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_early_price_view_is_read_only_and_has_no_model_outputs(tmp_path: Path) -> None:
    ledger = tmp_path / "prospective.jsonl"
    evidence = tmp_path / "evidence.json"
    ledger.write_bytes(b"existing ledger")
    evidence.write_bytes(b"existing evidence")

    result = _run(tmp_path, _snapshot())

    assert result.returncode == 0
    assert result.stderr == ""
    assert "GRIDIRON THREE-BOOK EXPLORATORY PRICE VIEWER" in result.stdout
    assert "NON-PROSPECTIVE" in result.stdout
    assert "MODEL OUTPUTS: DISABLED" in result.stdout
    assert "Game: BUF @ NYJ" in result.stdout
    assert "Minutes to kickoff: 240.0" in result.stdout
    assert "View: EARLY PREGAME" in result.stdout
    assert "BetMGM: +120 / -140" in result.stdout
    assert "FanDuel: +121 / -141" in result.stdout
    assert "DraftKings: +122 / -142" in result.stdout
    assert "No prospective ledger written." in result.stdout
    assert "No prospective evidence created." in result.stdout
    assert "Model home probability" not in result.stdout
    assert "Selected edge" not in result.stdout
    assert "Final decision" not in result.stdout
    assert ledger.read_bytes() == b"existing ledger"
    assert evidence.read_bytes() == b"existing evidence"


def test_near_kickoff_uses_actual_timestamp_and_minutes(tmp_path: Path) -> None:
    result = _run(tmp_path, _snapshot(captured_at="2026-09-13T16:00:00Z"))
    assert result.returncode == 0
    assert "Captured: 2026-09-13T16:00:00Z" in result.stdout
    assert "Minutes to kickoff: 60.0" in result.stdout
    assert "View: FINAL / NEAR-KICKOFF" in result.stdout


def test_missing_and_stale_book_data_produce_warnings(tmp_path: Path) -> None:
    snapshot = _snapshot()
    snapshot["offers"] = snapshot["offers"][:2]
    snapshot["offers"][0]["observed_at"] = "2026-09-13T12:00:00Z"
    snapshot["offers"][1]["away_odds"] = None

    result = _run(tmp_path, snapshot)

    assert result.returncode == 0
    assert "BetMGM:STALE_PRICE_60.0_MINUTES" in result.stdout
    assert "FanDuel:MISSING_PRICE" in result.stdout
    assert "DraftKings:MISSING_BOOK" in result.stdout
    assert "DraftKings: N/A / N/A" in result.stdout


@pytest.mark.parametrize(
    "mutation",
    [
        lambda item: item.update(captured_at="not-a-time"),
        lambda item: item["offers"].append(deepcopy(item["offers"][0])),
        lambda item: item["offers"][0].update(book="UnknownBook"),
        lambda item: item["offers"][0].update(home_odds=0),
    ],
)
def test_invalid_input_returns_clean_error_without_traceback(
    tmp_path: Path, mutation
) -> None:
    snapshot = _snapshot()
    mutation(snapshot)
    result = _run(tmp_path, snapshot)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr


def test_existing_step91d_report_is_unchanged() -> None:
    source = (ROOT / "scripts" / "step91d_market_ingestion.py").read_text(
        encoding="utf-8"
    )
    assert "GRIDIRON WEEK 1 MARKET PREVIEW" in source
    assert "preview_market_decision(snapshot)" in source
    assert "step91d_three_book_exploratory" not in source
