from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime

import pytest

from gridiron.market.operational_totals import (
    AUTOMATIC_PROVIDER_PREFIX,
    OperationalTotalsError,
    append_totals_observation,
    build_totals_observation,
    canonical_json,
)
from gridiron.market.totals_collection_attempts import (
    TotalsAttemptError,
    append_totals_attempt,
    build_totals_attempt,
)
from scripts.gridiron_totals_health import inspect_totals_health

NOW = datetime(2026, 9, 13, 5, tzinfo=UTC)
GAME = {"game_id": "2026_01_ATL_PIT", "season": 2026, "week": 1, "season_type": "REG", "home_team": "PIT", "away_team": "ATL", "kickoff_at": "2026-09-13T17:00:00Z"}


def observation():
    stamp = NOW.isoformat().replace("+00:00", "Z")
    books = [
        {"bookmaker_key": key, "bookmaker": name, "total": 47.5, "over_price": -110, "under_price": -110, "observed_at": stamp}
        for key, name in (("betmgm", "BetMGM"), ("fanduel", "FanDuel"), ("draftkings", "DraftKings"))
    ]
    return build_totals_observation(GAME, books, collected_at=NOW, target_label="T12H", provider=AUTOMATIC_PROVIDER_PREFIX + "T12H")


def test_empty_state_is_valid_and_read_only(tmp_path) -> None:
    history, attempts = tmp_path / "history.jsonl", tmp_path / "attempts.jsonl"
    before = set(tmp_path.iterdir())
    report = inspect_totals_health(history, attempts)
    assert report["status"] == "READY"
    assert report["observation_count"] == report["attempt_count"] == 0
    assert set(tmp_path.iterdir()) == before


def test_valid_linked_state_and_orphan_recovery_status(tmp_path) -> None:
    history, attempts = tmp_path / "history.jsonl", tmp_path / "attempts.jsonl"
    row = observation()
    append_totals_observation(history, row)
    assert inspect_totals_health(history, attempts)["status"] == "RECOVERY_REQUIRED"
    attempt = build_totals_attempt(game_id=GAME["game_id"], target_label="T12H", kickoff_at=GAME["kickoff_at"], attempted_at=NOW, result="SUCCESS", reason_code="SUCCESS", observation_id=row["observation_id"])
    append_totals_attempt(attempts, attempt)
    report = inspect_totals_health(history, attempts)
    assert report["status"] == "READY"
    assert report["success_count"] == 1
    assert report["latest_target_label"] == "T12H"


@pytest.mark.parametrize("content", ["not-json\n", "{}\n"])
def test_malformed_or_broken_hash_fails_closed(tmp_path, content: str) -> None:
    history = tmp_path / "history.jsonl"
    history.write_text(content, encoding="utf-8")
    with pytest.raises(OperationalTotalsError):
        inspect_totals_health(history, tmp_path / "attempts.jsonl")


def test_orphan_success_attempt_fails_closed(tmp_path) -> None:
    attempts = tmp_path / "attempts.jsonl"
    attempt = build_totals_attempt(game_id=GAME["game_id"], target_label="T12H", kickoff_at=GAME["kickoff_at"], attempted_at=NOW, result="SUCCESS", reason_code="SUCCESS", observation_id="a" * 64)
    append_totals_attempt(attempts, attempt)
    with pytest.raises(TotalsAttemptError):
        inspect_totals_health(tmp_path / "history.jsonl", attempts)


def test_self_hashed_bad_provider_and_duplicate_target_fail(tmp_path) -> None:
    history = tmp_path / "history.jsonl"
    row = observation()
    bad = deepcopy(row)
    bad["provider"] = AUTOMATIC_PROVIDER_PREFIX + "WRONG"
    bad.pop("observation_id")
    bad["observation_id"] = hashlib.sha256(canonical_json(bad).encode()).hexdigest()
    history.write_text(canonical_json(bad) + "\n", encoding="utf-8")
    with pytest.raises(OperationalTotalsError):
        inspect_totals_health(history, tmp_path / "attempts.jsonl")
    history.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(OperationalTotalsError):
        inspect_totals_health(history, tmp_path / "attempts.jsonl")
