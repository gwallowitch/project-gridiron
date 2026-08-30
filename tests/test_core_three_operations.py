from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from gridiron.market.core_three_operations import preview_non_evidence
from gridiron.market.core_three_types import CoreThreeError
from test_core_three_provider import authoritative, response


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/step91o_core_three_protocol_v1.json"


def test_config_is_inactive_exact_and_non_evidence() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["provider"]["exact_bookmaker_keys"] == [
        "betmgm",
        "fanduel",
        "draftkings",
    ]
    assert config["markets"]["required_keys"] == ["h2h", "spreads", "totals"]
    assert config["consensus"]["weight_per_book"] == "1/3"
    assert config["retention"]["raw_payload_archival"] is False
    assert config["activation_allowed"] is False
    assert config["prospective_evidence_count"] == 0


def test_preview_is_sanitized_and_cannot_create_evidence(tmp_path: Path) -> None:
    before = list(tmp_path.iterdir())
    preview = preview_non_evidence(
        response(),
        authoritative(),
        receipt_at="2026-09-09T23:20:00Z",
        timestamp_semantics_approved_for_test=True,
    )
    assert preview["activation_allowed"] is False
    assert preview["prospective_evidence_count"] == 0
    assert preview["manifest_touched"] is False
    assert preview["ledger_touched"] is False
    assert preview["raw_payload_retained"] is False
    assert list(tmp_path.iterdir()) == before
    assert "apiKey" not in json.dumps(preview)


def test_default_preview_refuses_unresolved_timestamp_gate() -> None:
    with pytest.raises(CoreThreeError, match="TIMESTAMP_SEMANTICS_UNAPPROVED"):
        preview_non_evidence(
            response(), authoritative(), receipt_at="2026-09-09T23:20:00Z"
        )


def test_mixed_event_data_rejects_atomically() -> None:
    payload = response()
    payload["bookmakers"][2]["markets"][0]["outcomes"][0]["name"] = (
        "San Francisco 49ers"
    )
    with pytest.raises(CoreThreeError, match="TEAM_OUTCOME_MISMATCH"):
        preview_non_evidence(
            payload,
            authoritative(),
            receipt_at="2026-09-09T23:20:00Z",
            timestamp_semantics_approved_for_test=True,
        )


def test_preview_only_cli_is_non_evidence_and_writes_nothing_else(
    tmp_path: Path,
) -> None:
    response_path = tmp_path / "response.json"
    event_path = tmp_path / "event.json"
    response_path.write_text(json.dumps(response()), encoding="utf-8")
    event_path.write_text(json.dumps(authoritative()), encoding="utf-8")
    before = sorted(path.name for path in tmp_path.iterdir())
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/step91o_core_three.py"),
            "--response",
            str(response_path),
            "--authoritative-event",
            str(event_path),
            "--receipt-at",
            "2026-09-09T23:20:00Z",
            "--test-timestamp-semantics-approved",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["activation_allowed"] is False
    assert output["prospective_evidence_count"] == 0
    assert sorted(path.name for path in tmp_path.iterdir()) == before
