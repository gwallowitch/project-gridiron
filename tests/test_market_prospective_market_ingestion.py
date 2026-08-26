from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from gridiron.market.prospective_ledger import (
    CANDIDATE_ID,
    CONSENSUS_BOOKS,
    EXECUTION_BOOK,
    PROTOCOL_ID,
    validate_ledger,
)
from gridiron.market.prospective_market_ingestion import (
    BOOK_ALIASES,
    ProspectiveMarketIngestionError,
    build_ledger_payload,
    capture_market_decision,
    load_market_snapshot,
    normalize_market_snapshot,
    preview_market_decision,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "step91d_market_ingestion.py"


def _snapshot(**updates: object) -> dict[str, object]:
    raw: dict[str, object] = {
        "schema_version": 1,
        "provider": "manual",
        "captured_at": "2026-09-13T14:00:00Z",
        "game": {
            "game_id": "2026_01_BUF_NYJ",
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
                "home_odds": 120 + index,
                "away_odds": -140 - index,
                "observed_at": "2026-09-13T13:55:00Z",
            }
            for index, book in enumerate(CONSENSUS_BOOKS)
        ],
    }
    raw.update(updates)
    return raw


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_valid_snapshot_produces_step91c_decision() -> None:
    event = preview_market_decision(_snapshot())
    assert event["event_type"] == "DECISION"
    assert event["protocol_id"] == PROTOCOL_ID
    assert event["candidate_id"] == CANDIDATE_ID


def test_preview_does_not_create_or_modify_ledger(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    preview_market_decision(_snapshot())
    assert not ledger.exists()
    ledger.write_bytes(b"existing")
    preview_market_decision(_snapshot())
    assert ledger.read_bytes() == b"existing"


def test_capture_appends_exactly_one_valid_decision(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    event = capture_market_decision(ledger, _snapshot())
    assert validate_ledger(ledger).decisions[event["game_id"]] == event
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_reordered_offers_are_identical() -> None:
    first = _snapshot()
    second = deepcopy(first)
    second["offers"] = list(reversed(second["offers"]))
    assert build_ledger_payload(first) == build_ledger_payload(second)
    event1 = preview_market_decision(first)
    event2 = preview_market_decision(second)
    assert event1["event_id"] == event2["event_id"]
    assert event1["observation_id"] == event2["observation_id"]


def test_explicit_aliases_normalize_to_canonical_order() -> None:
    raw = _snapshot()
    aliases = [
        "bet365",
        "Sports Illustrated",
        "betway",
        "Bet MGM",
        "Fan Duel",
        "Caesars Sportsbook",
        "Draft Kings",
    ]
    for offer, alias in zip(raw["offers"], aliases, strict=True):
        offer["book"] = alias
    payload = build_ledger_payload(raw)
    assert [item["book"] for item in payload["market_observations"]] == list(
        CONSENSUS_BOOKS
    )


def test_latest_observation_is_selected() -> None:
    raw = _snapshot()
    raw["offers"].append(
        raw["offers"][0]
        | {"home_odds": 200, "observed_at": "2026-09-13T13:59:00Z"}
    )
    assert build_ledger_payload(raw)["market_observations"][0]["home_odds"] == 200


def test_fractional_timestamp_selection_uses_time_not_text_order() -> None:
    raw = _snapshot()
    raw["offers"][0]["observed_at"] = "2026-09-13T13:55:00Z"
    raw["offers"].append(
        raw["offers"][0]
        | {"home_odds": 200, "observed_at": "2026-09-13T13:55:00.9Z"}
    )
    selected = build_ledger_payload(raw)["market_observations"][0]
    assert selected["home_odds"] == 200
    assert selected["observed_at"] == "2026-09-13T13:55:00.900000Z"


def test_future_observation_is_rejected() -> None:
    raw = _snapshot()
    raw["offers"][0]["observed_at"] = "2026-09-13T14:00:01Z"
    with pytest.raises(ProspectiveMarketIngestionError, match="later than"):
        normalize_market_snapshot(raw)


def test_observation_equal_to_capture_is_accepted() -> None:
    raw = _snapshot()
    raw["offers"][0]["observed_at"] = raw["captured_at"]
    assert build_ledger_payload(raw)["market_observations"][0]["observed_at"] == raw[
        "captured_at"
    ]


def test_identical_latest_duplicates_collapse() -> None:
    raw = _snapshot()
    raw["offers"].append(deepcopy(raw["offers"][0]))
    assert len(build_ledger_payload(raw)["market_observations"]) == 7


def test_conflicting_latest_duplicates_are_rejected() -> None:
    raw = _snapshot()
    raw["offers"].append(raw["offers"][0] | {"home_odds": 200})
    with pytest.raises(ProspectiveMarketIngestionError, match="ambiguous latest"):
        normalize_market_snapshot(raw)


def test_missing_book_lists_books_in_canonical_order() -> None:
    raw = _snapshot()
    raw["offers"] = [item for item in raw["offers"] if item["book"] not in {"SI", "FanDuel"}]
    with pytest.raises(ProspectiveMarketIngestionError, match="SI, FanDuel"):
        normalize_market_snapshot(raw)


def test_unexpected_book_is_rejected() -> None:
    raw = _snapshot()
    raw["offers"][0]["book"] = "Unknown"
    with pytest.raises(ProspectiveMarketIngestionError, match="recognized explicit"):
        normalize_market_snapshot(raw)


def test_non_moneyline_market_is_rejected() -> None:
    raw = _snapshot()
    raw["offers"][0]["market"] = "spread"
    with pytest.raises(ProspectiveMarketIngestionError, match="moneyline"):
        normalize_market_snapshot(raw)


def test_mismatched_teams_are_rejected() -> None:
    raw = _snapshot()
    raw["offers"][0]["home_team"] = "BUF"
    with pytest.raises(ProspectiveMarketIngestionError, match="teams"):
        normalize_market_snapshot(raw)


@pytest.mark.parametrize("odds", [0, -99, 99, 100.0, True])
def test_invalid_american_odds_are_rejected(odds: object) -> None:
    raw = _snapshot()
    raw["offers"][0]["home_odds"] = odds
    with pytest.raises(ProspectiveMarketIngestionError, match="home_odds"):
        normalize_market_snapshot(raw)


@pytest.mark.parametrize("field", ["captured_at", "kickoff_at", "observed_at"])
def test_naive_timestamps_are_rejected(field: str) -> None:
    raw = _snapshot()
    if field == "captured_at":
        raw[field] = "2026-09-13T14:00:00"
    elif field == "kickoff_at":
        raw["game"][field] = "2026-09-13T17:00:00"
    else:
        raw["offers"][0][field] = "2026-09-13T13:55:00"
    with pytest.raises(ProspectiveMarketIngestionError, match="timezone"):
        normalize_market_snapshot(raw)


@pytest.mark.parametrize("captured", ["2026-09-13T17:00:00Z", "2026-09-13T18:00:00Z"])
def test_capture_at_or_after_kickoff_is_rejected(captured: str) -> None:
    with pytest.raises(ProspectiveMarketIngestionError, match="strictly earlier"):
        normalize_market_snapshot(_snapshot(captured_at=captured))


def test_non_2026_season_is_rejected() -> None:
    raw = _snapshot()
    raw["game"]["season"] = 2025
    with pytest.raises(ProspectiveMarketIngestionError, match="2026"):
        normalize_market_snapshot(raw)


def test_non_reg_season_type_is_rejected() -> None:
    raw = _snapshot()
    raw["game"]["season_type"] = "POST"
    with pytest.raises(ProspectiveMarketIngestionError, match="REG"):
        normalize_market_snapshot(raw)


@pytest.mark.parametrize("week", [0, 17, True])
def test_invalid_weeks_are_rejected(week: object) -> None:
    raw = _snapshot()
    raw["game"]["week"] = week
    with pytest.raises(ProspectiveMarketIngestionError, match="week"):
        normalize_market_snapshot(raw)


def test_week_one_null_def_epa_reaches_step91c_as_zero() -> None:
    assert build_ledger_payload(_snapshot())["def_epa"] is None
    assert preview_market_decision(_snapshot())["def_epa"] == 0.0


def test_later_week_null_def_epa_is_rejected_before_mutation(tmp_path: Path) -> None:
    raw = _snapshot()
    raw["game"]["week"] = 2
    ledger = tmp_path / "ledger.jsonl"
    with pytest.raises(ProspectiveMarketIngestionError, match="Week 1"):
        capture_market_decision(ledger, raw)
    assert not ledger.exists()


def test_draftkings_observation_becomes_execution_prices() -> None:
    payload = build_ledger_payload(_snapshot())
    draftkings = payload["market_observations"][-1]
    assert payload["execution_prices"] == {
        "book": EXECUTION_BOOK,
        "home_odds": draftkings["home_odds"],
        "away_odds": draftkings["away_odds"],
    }


def test_provider_does_not_affect_event_identity() -> None:
    assert preview_market_decision(_snapshot(provider="one"))["event_id"] == (
        preview_market_decision(_snapshot(provider="two"))["event_id"]
    )


def test_duplicate_capture_is_rejected_by_step91c(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    capture_market_decision(ledger, _snapshot())
    with pytest.raises(ProspectiveMarketIngestionError, match="duplicate"):
        capture_market_decision(ledger, _snapshot())


def test_rejected_capture_preserves_existing_ledger_bytes(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    capture_market_decision(ledger, _snapshot())
    before = ledger.read_bytes()
    invalid = _snapshot()
    invalid["offers"][0]["book"] = "unexpected"
    with pytest.raises(ProspectiveMarketIngestionError):
        capture_market_decision(ledger, invalid)
    assert ledger.read_bytes() == before


def test_cli_preview_prints_canonical_json_without_ledger(tmp_path: Path) -> None:
    source = tmp_path / "snapshot.json"
    _write(source, _snapshot())
    result = _run("--input", str(source), "preview")
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == json.dumps(
        preview_market_decision(_snapshot()),
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def test_cli_capture_requires_ledger_and_appends_one(tmp_path: Path) -> None:
    source = tmp_path / "snapshot.json"
    ledger = tmp_path / "ledger.jsonl"
    _write(source, _snapshot())
    missing = _run("--input", str(source), "capture")
    assert missing.returncode != 0
    result = _run("--input", str(source), "--ledger", str(ledger), "capture")
    assert result.returncode == 0
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 1


def test_cli_validation_error_has_no_traceback(tmp_path: Path) -> None:
    source = tmp_path / "snapshot.json"
    raw = _snapshot()
    raw["offers"][0]["home_odds"] = 0
    _write(source, raw)
    result = _run("--input", str(source), "preview")
    assert result.returncode != 0
    assert "error:" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout == ""


def test_frozen_constants_match_authoritative_step91c() -> None:
    assert tuple(dict.fromkeys(BOOK_ALIASES.values())) == CONSENSUS_BOOKS
    assert EXECUTION_BOOK == "DraftKings"
    assert PROTOCOL_ID == "step91b-prospective-validation-v1"
    assert CANDIDATE_ID == "market-plus-def-epa-capped-0425-v1"


@pytest.mark.parametrize("level", ["top", "game", "offer"])
def test_unknown_keys_are_rejected_at_every_level(level: str) -> None:
    raw = _snapshot()
    target = raw if level == "top" else raw["game"] if level == "game" else raw["offers"][0]
    target["unknown"] = 1
    with pytest.raises(ProspectiveMarketIngestionError, match="unknown keys"):
        normalize_market_snapshot(raw)


def test_strict_json_rejects_nan(tmp_path: Path) -> None:
    source = tmp_path / "snapshot.json"
    source.write_text('{"value":NaN}', encoding="utf-8")
    with pytest.raises(ProspectiveMarketIngestionError, match="numeric constant"):
        load_market_snapshot(source)
