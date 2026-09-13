from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from gridiron.market.operational_totals import (
    AUTOMATIC_PROVIDER_PREFIX,
    CLASSIFICATION,
    OperationalTotalsError,
    append_totals_observation,
    build_totals_observation,
    canonical_json,
    parse_totals_payload,
    read_totals_history,
)

NOW = datetime(2026, 9, 13, 5, 0, tzinfo=UTC)
GAME = {"game_id": "2026_01_ATL_PIT", "season": 2026, "week": 1, "season_type": "REG", "home_team": "PIT", "away_team": "ATL", "kickoff_at": "2026-09-13T17:00:00Z"}


def payload() -> list[dict[str, object]]:
    stamp = NOW.isoformat().replace("+00:00", "Z")
    return [{"home_team": "Pittsburgh Steelers", "away_team": "Atlanta Falcons", "bookmakers": [
        {"key": key, "last_update": stamp, "markets": [{"key": "totals", "outcomes": [
            {"name": "Over", "price": -110, "point": 47.5},
            {"name": "Under", "price": -110, "point": 47.5},
        ]}]} for key in ("betmgm", "fanduel", "draftkings")]}]


def books(data: object | None = None):
    return parse_totals_payload(payload() if data is None else data, home_name="Pittsburgh Steelers", away_name="Atlanta Falcons", collected_at=NOW)


def observation():
    return build_totals_observation(GAME, books(), collected_at=NOW, target_label="T12H", provider=AUTOMATIC_PROVIDER_PREFIX + "T12H")


def rehash(row: dict[str, object]) -> dict[str, object]:
    result = deepcopy(row)
    result.pop("observation_id", None)
    result["observation_id"] = hashlib.sha256(canonical_json(result).encode()).hexdigest()
    return result


def test_valid_three_book_totals_parse_and_canonical_observation() -> None:
    parsed = books()
    assert [row["bookmaker"] for row in parsed] == ["BetMGM", "FanDuel", "DraftKings"]
    row = observation()
    assert row["classification"] == CLASSIFICATION
    assert row["prospective_evidence"] is False
    assert "edge" not in canonical_json(row).lower()


@pytest.mark.parametrize("case", ["missing_book", "missing_market", "missing_over", "missing_under", "mismatch", "bad_price", "missing_time", "bad_time", "future", "nan", "inf", "duplicate_market"])
def test_provider_payload_fails_closed(case: str) -> None:
    data = payload()
    bookmaker = data[0]["bookmakers"][0]
    outcomes = bookmaker["markets"][0]["outcomes"]
    if case == "missing_book": data[0]["bookmakers"].pop()
    elif case == "missing_market": bookmaker["markets"] = []
    elif case == "missing_over": outcomes.pop(0)
    elif case == "missing_under": outcomes.pop()
    elif case == "mismatch": outcomes[1]["point"] = 48.0
    elif case == "bad_price": outcomes[0]["price"] = 50
    elif case == "missing_time": bookmaker.pop("last_update")
    elif case == "bad_time": bookmaker["last_update"] = "invalid"
    elif case == "future": bookmaker["last_update"] = (NOW + timedelta(minutes=1)).isoformat()
    elif case == "nan": outcomes[0]["point"] = float("nan")
    elif case == "inf": outcomes[0]["point"] = float("inf")
    else: bookmaker["markets"].append(deepcopy(bookmaker["markets"][0]))
    with pytest.raises(OperationalTotalsError):
        books(data)


def test_history_round_trip_duplicate_and_tamper_detection(tmp_path: Path) -> None:
    path = tmp_path / "totals.jsonl"
    row = observation()
    append_totals_observation(path, row)
    assert read_totals_history(path) == (row,)
    before = path.read_bytes()
    with pytest.raises(OperationalTotalsError):
        append_totals_observation(path, row)
    assert path.read_bytes() == before
    bad = deepcopy(row)
    bad["books"][0]["total"] = 200.0
    path.write_text(canonical_json(rehash(bad)) + "\n", encoding="utf-8")
    with pytest.raises(OperationalTotalsError):
        read_totals_history(path)


def test_semantic_duplicate_game_target_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "totals.jsonl"
    append_totals_observation(path, observation())
    later = NOW + timedelta(minutes=1)
    other = build_totals_observation(
        GAME, parse_totals_payload(payload(), home_name="Pittsburgh Steelers", away_name="Atlanta Falcons", collected_at=NOW),
        collected_at=later, target_label="T12H", provider=AUTOMATIC_PROVIDER_PREFIX + "T12H",
    )
    with pytest.raises(OperationalTotalsError):
        append_totals_observation(path, other)


def test_self_hashed_classification_provider_and_postkickoff_fail(tmp_path: Path) -> None:
    for mutation in ("classification", "provider", "postkickoff"):
        row = observation()
        if mutation == "classification": row["classification"] = "PROSPECTIVE"
        elif mutation == "provider": row["provider"] = "wrong"
        else:
            row["timing"]["collected_at"] = "2026-09-13T18:00:00Z"
            row["timing"]["minutes_before_kickoff"] = -60.0
            row["timing"]["target_deviation_minutes"] = -780.0
        path = tmp_path / f"{mutation}.jsonl"
        path.write_text(canonical_json(rehash(row)) + "\n", encoding="utf-8")
        with pytest.raises(OperationalTotalsError):
            read_totals_history(path)
