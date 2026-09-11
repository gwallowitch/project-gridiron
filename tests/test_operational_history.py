from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from gridiron.market.operational_history import (
    CLASSIFICATION,
    DuplicateOperationalObservationError,
    OperationalHistoryError,
    append_operational_observation,
    build_operational_history_record,
    canonical_json,
    read_operational_history,
)
from scripts.gridiron_operational_prediction import (
    OperationalPredictionError,
    build_operational_prediction,
)

BOOKS = ("BetMGM", "FanDuel", "DraftKings")


def snapshot(
    *,
    captured_at: str = "2026-09-09T18:20:00Z",
    observed_at: str = "2026-09-09T18:19:00Z",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "provider": "the-odds-api-operational",
        "captured_at": captured_at,
        "game": {
            "game_id": "2026_01_NE_SEA",
            "season": 2026,
            "week": 1,
            "season_type": "REG",
            "home_team": "SEA",
            "away_team": "NE",
            "kickoff_at": "2026-09-10T00:20:00Z",
        },
        "offers": [
            {
                "book": book,
                "home_odds": -175 - index,
                "away_odds": 145 + index,
                "observed_at": observed_at,
            }
            for index, book in enumerate(BOOKS)
        ],
    }


def prediction(
    *,
    captured_at: str = "2026-09-09T18:20:00Z",
    observed_at: str = "2026-09-09T18:19:00Z",
    def_epa: float = 0.0,
    source: str = "frozen Week 1 neutral rule",
) -> dict[str, object]:
    return build_operational_prediction(
        snapshot(captured_at=captured_at, observed_at=observed_at),
        def_epa=def_epa,
        def_epa_source=source,
    )


def rehash(record: dict[str, object]) -> dict[str, object]:
    material = deepcopy(record)
    material.pop("observation_id", None)
    material["observation_id"] = hashlib.sha256(
        canonical_json(material).encode("utf-8")
    ).hexdigest()
    return material


def write_record(path: Path, record: dict[str, object]) -> None:
    path.write_text(canonical_json(record) + "\n", encoding="utf-8")


def test_valid_observation_round_trips_required_provenance(tmp_path: Path) -> None:
    history = tmp_path / "operational.jsonl"
    written = append_operational_observation(history, prediction())
    assert read_operational_history(history) == (written,)
    assert written["classification"] == CLASSIFICATION
    assert written["prospective_evidence"] is False
    assert written["game"] == {
        "game_id": "2026_01_NE_SEA",
        "season": 2026,
        "week": 1,
        "season_type": "REG",
        "home_team": "SEA",
        "away_team": "NE",
        "kickoff_at": "2026-09-10T00:20:00Z",
    }
    assert [item["book"] for item in written["books"]] == list(BOOKS)
    assert all("home_no_vig_probability" in item for item in written["books"])
    assert written["def_epa"] == {
        "feature": "def_epa_trend_advantage",
        "value": 0.0,
        "source": "frozen Week 1 neutral rule",
    }
    assert written["decision"]["execution_book"] == "DraftKings"
    assert written["decision"]["break_even_probability"] is not None


def test_same_game_different_capture_times_are_retained(tmp_path: Path) -> None:
    history = tmp_path / "operational.jsonl"
    first = append_operational_observation(history, prediction())
    second = append_operational_observation(
        history,
        prediction(
            captured_at="2026-09-09T19:20:00Z",
            observed_at="2026-09-09T19:19:00Z",
        ),
    )
    assert len(read_operational_history(history)) == 2
    assert first["observation_id"] != second["observation_id"]


def test_exact_duplicate_is_rejected_without_mutation(tmp_path: Path) -> None:
    history = tmp_path / "operational.jsonl"
    result = prediction()
    append_operational_observation(history, result)
    before = history.read_bytes()
    with pytest.raises(DuplicateOperationalObservationError, match="already recorded"):
        append_operational_observation(history, result)
    assert history.read_bytes() == before


@pytest.mark.parametrize("content", [b"not json\n", b"\n"])
def test_corrupt_existing_history_prevents_append_without_mutation(
    tmp_path: Path, content: bytes
) -> None:
    history = tmp_path / "operational.jsonl"
    history.write_bytes(content)
    before = history.read_bytes()
    with pytest.raises(OperationalHistoryError):
        append_operational_observation(history, prediction())
    assert history.read_bytes() == before


def test_tampered_hash_is_rejected(tmp_path: Path) -> None:
    record = build_operational_history_record(prediction())
    record["provider"] = "tampered"
    path = tmp_path / "history.jsonl"
    path.write_text(canonical_json(record) + "\n", encoding="utf-8")
    with pytest.raises(OperationalHistoryError, match="identity"):
        read_operational_history(path)


def test_duplicate_identity_in_existing_file_is_rejected(tmp_path: Path) -> None:
    history = tmp_path / "operational.jsonl"
    record = build_operational_history_record(prediction())
    line = canonical_json(record) + "\n"
    history.write_text(line + line, encoding="utf-8")
    before = history.read_bytes()
    with pytest.raises(OperationalHistoryError, match="duplicate observation"):
        append_operational_observation(history, prediction())
    assert history.read_bytes() == before


def test_semantically_invalid_existing_history_blocks_append_without_mutation(
    tmp_path: Path,
) -> None:
    history = tmp_path / "operational.jsonl"
    record = build_operational_history_record(prediction())
    record["record_type"] = "OTHER"
    write_record(history, rehash(record))
    before = history.read_bytes()
    with pytest.raises(OperationalHistoryError, match="record_type"):
        append_operational_observation(history, prediction())
    assert history.read_bytes() == before


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 1, "schema_version"),
        ("record_type", "OTHER", "record_type"),
        ("classification", "PROSPECTIVE", "classification"),
        ("prospective_evidence", True, "exactly false"),
    ],
)
def test_self_hashed_invalid_contract_fields_are_rejected(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    record = build_operational_history_record(prediction())
    record[field] = value
    write_record(tmp_path / "history.jsonl", rehash(record))
    with pytest.raises(OperationalHistoryError, match=message):
        read_operational_history(tmp_path / "history.jsonl")


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unexpected"])
def test_invalid_book_identity_is_rejected(tmp_path: Path, mutation: str) -> None:
    record = build_operational_history_record(prediction())
    if mutation == "missing":
        record["books"] = record["books"][:-1]
    elif mutation == "duplicate":
        record["books"][2] = deepcopy(record["books"][0])
    else:
        record["books"][2]["book"] = "OtherBook"
    write_record(tmp_path / "history.jsonl", rehash(record))
    with pytest.raises(OperationalHistoryError):
        read_operational_history(tmp_path / "history.jsonl")


def test_non_draftkings_execution_is_rejected(tmp_path: Path) -> None:
    record = build_operational_history_record(prediction())
    record["decision"]["execution_book"] = "FanDuel"
    write_record(tmp_path / "history.jsonl", rehash(record))
    with pytest.raises(OperationalHistoryError, match="DraftKings"):
        read_operational_history(tmp_path / "history.jsonl")


@pytest.mark.parametrize(
    ("kickoff", "minutes"),
    [
        ("2026-09-09T18:20:00Z", 0.0),
        ("2026-09-09T18:19:00Z", -1.0),
    ],
)
def test_at_or_post_kickoff_record_is_rejected(
    tmp_path: Path, kickoff: str, minutes: float
) -> None:
    record = build_operational_history_record(prediction())
    record["game"]["kickoff_at"] = kickoff
    record["timing"]["minutes_to_kickoff"] = minutes
    record["timing"]["hours_to_kickoff"] = minutes / 60.0
    write_record(tmp_path / "history.jsonl", rehash(record))
    with pytest.raises(OperationalHistoryError, match="pre-kickoff"):
        read_operational_history(tmp_path / "history.jsonl")


def test_non_finite_required_number_is_rejected(tmp_path: Path) -> None:
    record = build_operational_history_record(prediction())
    record["market"]["home_probability"] = float("nan")
    material = deepcopy(record)
    material.pop("observation_id")
    line = json.dumps(material, allow_nan=True, sort_keys=True)
    history = tmp_path / "history.jsonl"
    history.write_text(line, encoding="utf-8")
    with pytest.raises(OperationalHistoryError):
        read_operational_history(history)


def test_decision_is_bet_and_edge_consistency_is_enforced(tmp_path: Path) -> None:
    record = build_operational_history_record(prediction())
    record["decision"]["is_bet"] = not record["decision"]["is_bet"]
    write_record(tmp_path / "history.jsonl", rehash(record))
    with pytest.raises(OperationalHistoryError, match="strict edge"):
        read_operational_history(tmp_path / "history.jsonl")


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("book", "home_no_vig_probability"),
        ("market", "home_probability"),
        ("model", "home_probability"),
        ("decision", "edge"),
    ],
)
def test_self_hashed_derived_value_tampering_is_rejected(
    tmp_path: Path, section: str, field: str
) -> None:
    record = build_operational_history_record(prediction())
    if section == "book":
        record["books"][0][field] += 0.01
    else:
        record[section][field] += 0.01
    write_record(tmp_path / "history.jsonl", rehash(record))
    with pytest.raises(OperationalHistoryError, match="inconsistent"):
        read_operational_history(tmp_path / "history.jsonl")


def test_week_one_def_epa_provenance_cannot_be_relabelled(tmp_path: Path) -> None:
    record = build_operational_history_record(prediction())
    record["def_epa"]["source"] = "caller-supplied"
    write_record(tmp_path / "history.jsonl", rehash(record))
    with pytest.raises(OperationalHistoryError, match="frozen neutral rule"):
        read_operational_history(tmp_path / "history.jsonl")


def test_informational_timing_warning_is_allowed(tmp_path: Path) -> None:
    result = prediction(
        captured_at="2026-09-09T22:20:00Z",
        observed_at="2026-09-09T22:19:00Z",
    )
    assert result["warnings"] == ("OUTSIDE_EARLY_AND_NEAR_KICKOFF_WINDOWS",)
    append_operational_observation(tmp_path / "history.jsonl", result)
    assert len(read_operational_history(tmp_path / "history.jsonl")) == 1


def test_blocking_market_warning_is_rejected_even_when_self_hashed(
    tmp_path: Path,
) -> None:
    record = build_operational_history_record(prediction())
    record["warnings"] = ["BetMGM:STALE_PRICE_11.0_MINUTES"]
    write_record(tmp_path / "history.jsonl", rehash(record))
    with pytest.raises(OperationalHistoryError, match="blocking market warning"):
        read_operational_history(tmp_path / "history.jsonl")


def test_formal_prospective_artifacts_are_not_touched(tmp_path: Path) -> None:
    history = tmp_path / "operational" / "history.jsonl"
    ledger = tmp_path / "prospective" / "ledger.jsonl"
    evidence = tmp_path / "prospective" / "evidence.json"
    ledger.parent.mkdir()
    ledger.write_bytes(b"ledger")
    evidence.write_bytes(b"evidence")
    append_operational_observation(history, prediction())
    assert ledger.read_bytes() == b"ledger"
    assert evidence.read_bytes() == b"evidence"


def test_invalid_or_stale_market_never_reaches_persistence(tmp_path: Path) -> None:
    history = tmp_path / "operational.jsonl"
    missing = snapshot()
    missing["offers"] = missing["offers"][:-1]
    stale = deepcopy(snapshot())
    stale["offers"][0]["observed_at"] = "2026-09-09T17:00:00Z"
    for invalid in (missing, stale):
        with pytest.raises(OperationalPredictionError):
            result = build_operational_prediction(invalid, def_epa=0.0)
            append_operational_observation(history, result)
    assert not history.exists()


def test_later_week_automatic_def_epa_provenance_survives(tmp_path: Path) -> None:
    result = prediction(
        def_epa=0.123456,
        source="automatic nflverse frozen feature",
    )
    result["week"] = 2
    result["game_id"] = "2026_02_NE_SEA"
    written = append_operational_observation(tmp_path / "history.jsonl", result)
    assert written["def_epa"]["value"] == 0.123456
    assert written["def_epa"]["source"] == "automatic nflverse frozen feature"


def test_serialized_record_is_canonical_json(tmp_path: Path) -> None:
    history = tmp_path / "operational.jsonl"
    append_operational_observation(history, prediction())
    line = history.read_text(encoding="utf-8").strip()
    assert json.loads(line)["schema_version"] == 2
    assert line.startswith('{"books":')
