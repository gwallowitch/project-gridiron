from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from gridiron.market.collection_attempts import (
    CollectionAttemptError,
    append_collection_attempt,
    build_collection_attempt,
    read_collection_attempts,
)
from gridiron.market.operational_history import read_operational_history
from scripts import gridiron_game_day as game_day
from scripts import gridiron_market_collector as collector

KICKOFF = datetime(2026, 9, 20, 17, 0, tzinfo=UTC)
PRICES = {
    "BetMGM": (-175, 145),
    "FanDuel": (-176, 146),
    "DraftKings": (-177, 147),
}
CREDENTIAL_VALUE = "credential-must-not-be-persisted"


def game(game_id: str = "2026_02_NE_SEA") -> dict[str, object]:
    return {
        "game_id": game_id,
        "season": 2026,
        "week": 2,
        "season_type": "REG",
        "home_team": "SEA",
        "away_team": "NE",
        "kickoff_at": KICKOFF.isoformat().replace("+00:00", "Z"),
    }


def write_schedule(path: Path, games: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(games), encoding="utf-8")


def paths(tmp_path: Path) -> tuple[Path, Path, Path]:
    schedule = tmp_path / "schedule.json"
    history = tmp_path / "history.jsonl"
    attempts = tmp_path / "attempts.jsonl"
    write_schedule(schedule, [game()])
    return schedule, history, attempts


def observed(now: datetime) -> dict[str, str]:
    stamp = now.isoformat().replace("+00:00", "Z")
    return {book: stamp for book in PRICES}


@pytest.mark.parametrize(
    ("label", "minutes"),
    [("T12H", 720), ("T6H", 360), ("T3H", 180), ("T1H", 60), ("NEAR_KICKOFF", 15)],
)
def test_each_fixed_window_is_eligible(label: str, minutes: int) -> None:
    assert collector.eligible_window(minutes).label == label


def test_outside_all_windows_makes_no_provider_request(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    calls = 0

    def fetch(_game: dict[str, object]):
        nonlocal calls
        calls += 1
        raise AssertionError

    result = collector.collect(
        now=KICKOFF - timedelta(minutes=500),
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=fetch,
    )
    assert calls == 0
    assert not history.exists()
    assert [item.reason_code for item in result] == ["MISSED_WINDOW"]


def test_post_kickoff_is_not_fetched_written_or_backfilled(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    result = collector.collect(
        now=KICKOFF + timedelta(minutes=1),
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=lambda _game: pytest.fail("provider called"),
    )
    assert result[0].result == "POST_KICKOFF"
    assert not history.exists()
    assert not attempts.exists()


def test_success_uses_one_fetch_one_history_and_linked_attempt(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    now = KICKOFF - timedelta(minutes=720)
    calls = 0

    def fetch(_game: dict[str, object]):
        nonlocal calls
        calls += 1
        return PRICES, observed(now)

    result = collector.collect(
        now=now,
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=fetch,
        def_epa_loader=lambda _game: 0.125,
    )
    history_rows = read_operational_history(history)
    attempt_rows = read_collection_attempts(attempts)
    assert calls == 1
    assert len(history_rows) == 1
    assert result[-1].result == "SUCCESS"
    assert attempt_rows[-1]["observation_id"] == history_rows[0]["observation_id"]
    assert "two_sided_execution" in history_rows[0]


def test_successful_target_is_exactly_once_without_refetch(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    now = KICKOFF - timedelta(minutes=720)
    calls = 0

    def fetch(_game: dict[str, object]):
        nonlocal calls
        calls += 1
        return PRICES, observed(now)

    kwargs = {
        "now": now,
        "schedule_path": schedule,
        "history_path": history,
        "attempt_path": attempts,
        "price_fetcher": fetch,
        "def_epa_loader": lambda _game: 0.125,
    }
    collector.collect(**kwargs)
    second = collector.collect(**kwargs)
    assert calls == 1
    assert any(item.result == "ALREADY_COMPLETE" for item in second)
    assert len(read_operational_history(history)) == 1


def test_missed_earlier_target_is_not_backfilled_but_later_target_runs(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    now = KICKOFF - timedelta(minutes=360)
    calls = 0

    def fetch(_game: dict[str, object]):
        nonlocal calls
        calls += 1
        return PRICES, observed(now)

    result = collector.collect(
        now=now,
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=fetch,
        def_epa_loader=lambda _game: 0.125,
    )
    by_target = {item.target: item for item in result}
    assert by_target["T12H"].result == "MISSED_WINDOW"
    assert by_target["T6H"].result == "SUCCESS"
    assert calls == 1
    assert len(read_operational_history(history)) == 1


def test_different_targets_for_same_game_are_retained(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    current = KICKOFF - timedelta(minutes=720)

    def fetch(_game: dict[str, object]):
        return PRICES, observed(current)

    for minutes in (720, 360):
        current = KICKOFF - timedelta(minutes=minutes)
        collector.collect(
            now=current,
            schedule_path=schedule,
            history_path=history,
            attempt_path=attempts,
            price_fetcher=fetch,
            def_epa_loader=lambda _game: 0.125,
        )
    successes = [row for row in read_collection_attempts(attempts) if row["result"] == "SUCCESS"]
    assert [row["collection_target"] for row in successes] == ["T12H", "T6H"]
    assert len(read_operational_history(history)) == 2


def test_games_are_independent_when_one_provider_call_fails(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    games = [game("2026_02_NE_SEA"), {**game("2026_02_NE_DEN"), "home_team": "DEN"}]
    write_schedule(schedule, games)
    now = KICKOFF - timedelta(minutes=720)
    calls = 0

    def fetch(selected: dict[str, object]):
        nonlocal calls
        calls += 1
        if selected["home_team"] == "SEA":
            raise game_day.GameDayInputError("live odds fetch failed")
        return PRICES, observed(now)

    result = collector.collect(
        now=now,
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=fetch,
        def_epa_loader=lambda _game: 0.125,
    )
    assert calls == 2
    assert [item.result for item in result] == ["FAILED", "SUCCESS"]
    assert len(read_operational_history(history)) == 1


def test_failed_collection_writes_attempt_but_no_fake_history(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    result = collector.collect(
        now=KICKOFF - timedelta(minutes=720),
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=lambda _game: (_ for _ in ()).throw(
            game_day.GameDayInputError("missing FanDuel")
        ),
        def_epa_loader=lambda _game: 0.125,
    )
    assert result[-1].reason_code == "MISSING_BOOK"
    assert not history.exists()
    assert len(read_collection_attempts(attempts)) == 1


def test_def_epa_failure_occurs_before_provider_credit(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    collector.collect(
        now=KICKOFF - timedelta(minutes=720),
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=lambda _game: pytest.fail("provider called"),
        def_epa_loader=lambda _game: (_ for _ in ()).throw(
            game_day.GameDayInputError("DEF EPA unavailable")
        ),
    )
    assert read_collection_attempts(attempts)[0]["reason_code"] == "DEF_EPA_UNAVAILABLE"


def test_dry_run_has_zero_provider_calls_and_zero_writes(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    result = collector.collect(
        now=KICKOFF - timedelta(minutes=720),
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        dry_run=True,
        price_fetcher=lambda _game: pytest.fail("provider called"),
    )
    assert result[-1].result == "DRY_RUN_ELIGIBLE"
    assert not history.exists()
    assert not attempts.exists()


def test_corrupt_history_fails_before_provider_call(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    history.write_text("not json\n", encoding="utf-8")
    with pytest.raises(Exception, match="invalid history JSON"):
        collector.collect(
            now=KICKOFF - timedelta(minutes=720),
            schedule_path=schedule,
            history_path=history,
            attempt_path=attempts,
            price_fetcher=lambda _game: pytest.fail("provider called"),
        )


def test_corrupt_attempt_log_fails_closed(tmp_path: Path) -> None:
    schedule, history, attempts = paths(tmp_path)
    attempts.write_text("not json\n", encoding="utf-8")
    with pytest.raises(CollectionAttemptError, match="invalid attempt JSON"):
        collector.collect(
            now=KICKOFF - timedelta(minutes=720),
            schedule_path=schedule,
            history_path=history,
            attempt_path=attempts,
        )


def test_duplicate_attempt_target_is_rejected_deterministically(tmp_path: Path) -> None:
    _, _, attempts = paths(tmp_path)
    record = build_collection_attempt(
        game_id=str(game()["game_id"]),
        collection_target="T12H",
        target_minutes_to_kickoff=720,
        kickoff_at=str(game()["kickoff_at"]),
        attempted_at=KICKOFF - timedelta(minutes=720),
        result="FAILED",
        reason_code="ODDS_PROVIDER_ERROR",
    )
    append_collection_attempt(attempts, record)
    with pytest.raises(CollectionAttemptError, match="already attempted"):
        append_collection_attempt(attempts, record)


def test_attempt_timing_metadata_is_derived_from_actual_timestamp() -> None:
    now = KICKOFF - timedelta(minutes=358)
    record = build_collection_attempt(
        game_id=str(game()["game_id"]),
        collection_target="T6H",
        target_minutes_to_kickoff=360,
        kickoff_at=str(game()["kickoff_at"]),
        attempted_at=now,
        result="FAILED",
        reason_code="ODDS_PROVIDER_ERROR",
    )
    assert record["actual_minutes_to_kickoff"] == 358.0
    assert record["target_deviation_minutes"] == -2.0
    assert record["target_time"] == (KICKOFF - timedelta(minutes=360)).isoformat().replace("+00:00", "Z")


def test_attempt_log_never_contains_api_credentials(tmp_path: Path) -> None:
    _, _, attempts = paths(tmp_path)
    record = build_collection_attempt(
        game_id=str(game()["game_id"]),
        collection_target="T12H",
        target_minutes_to_kickoff=720,
        kickoff_at=str(game()["kickoff_at"]),
        attempted_at=KICKOFF - timedelta(minutes=720),
        result="FAILED",
        reason_code="ODDS_PROVIDER_ERROR",
    )
    append_collection_attempt(attempts, record)
    assert CREDENTIAL_VALUE not in attempts.read_text(encoding="utf-8")


def test_attempt_append_failure_recovers_without_refetch_or_history_rewrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schedule, history, attempts = paths(tmp_path)
    now = KICKOFF - timedelta(minutes=720)
    fetches = 0

    def fetch(_game: dict[str, object]):
        nonlocal fetches
        fetches += 1
        return PRICES, observed(now)

    real_append = collector.append_collection_attempt
    monkeypatch.setattr(
        collector,
        "append_collection_attempt",
        lambda _path, _record: (_ for _ in ()).throw(
            CollectionAttemptError("simulated attempt append failure")
        ),
    )
    first = collector.collect(
        now=now,
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=fetch,
        def_epa_loader=lambda _game: 0.125,
    )
    original_bytes = history.read_bytes()
    assert first[-1].reason_code == "ATTEMPT_LOG_APPEND_FAILED"
    assert len(read_operational_history(history)) == 1
    assert not attempts.exists()

    monkeypatch.setattr(collector, "append_collection_attempt", real_append)
    second = collector.collect(
        now=now,
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=fetch,
        def_epa_loader=lambda _game: 0.125,
    )
    assert fetches == 1
    assert history.read_bytes() == original_bytes
    assert len(read_operational_history(history)) == 1
    assert second[-1].reason_code == "RECOVERED_SUCCESS"
    assert read_collection_attempts(attempts)[0]["observation_id"] == second[-1].observation_id


def test_manual_same_game_observation_is_not_reconciled_as_automatic(
    tmp_path: Path,
) -> None:
    schedule, history, attempts = paths(tmp_path)
    now = KICKOFF - timedelta(minutes=720)
    snapshot = game_day.build_game_day_snapshot(
        game(),
        PRICES,
        captured_at=now,
        observed_at=observed(now),
        provider="the-odds-api-operational",
    )
    prediction = game_day.build_operational_prediction(
        snapshot,
        def_epa=0.125,
        def_epa_source="automatic nflverse frozen feature",
    )
    from gridiron.market.operational_history import append_operational_observation

    append_operational_observation(history, prediction)
    fetches = 0

    def fetch(_game: dict[str, object]):
        nonlocal fetches
        fetches += 1
        return PRICES, observed(now)

    collector.collect(
        now=now,
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=fetch,
        def_epa_loader=lambda _game: 0.125,
    )
    assert fetches == 1
    assert len(read_operational_history(history)) == 2


def test_attempt_append_failure_isolated_per_game(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schedule, history, attempts = paths(tmp_path)
    games = [game("2026_02_NE_SEA"), {**game("2026_02_NE_DEN"), "home_team": "DEN"}]
    write_schedule(schedule, games)
    now = KICKOFF - timedelta(minutes=720)
    calls = 0
    real_append = collector.append_collection_attempt

    def flaky_append(path: Path | str, record: dict[str, object]) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise CollectionAttemptError("simulated attempt append failure")
        real_append(path, record)

    monkeypatch.setattr(collector, "append_collection_attempt", flaky_append)
    outcomes = collector.collect(
        now=now,
        schedule_path=schedule,
        history_path=history,
        attempt_path=attempts,
        price_fetcher=lambda _game: (PRICES, observed(now)),
        def_epa_loader=lambda _game: 0.125,
    )
    assert [item.reason_code for item in outcomes] == [
        "ATTEMPT_LOG_APPEND_FAILED",
        "SUCCESS",
    ]
    assert len(read_operational_history(history)) == 2
    assert len(read_collection_attempts(attempts)) == 1
