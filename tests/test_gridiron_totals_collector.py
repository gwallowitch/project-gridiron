from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from gridiron.market.operational_totals import (
    AUTOMATIC_PROVIDER_PREFIX,
    MANUAL_PROVIDER,
    OperationalTotalsError,
    append_totals_observation,
    build_totals_observation,
    canonical_json,
    read_totals_history,
)
from gridiron.market.totals_collection_attempts import read_totals_attempts
from scripts import gridiron_totals_collector as collector

KICKOFF = datetime(2026, 9, 20, 17, 0, tzinfo=UTC)


def game(game_id: str = "2026_02_NE_SEA", home: str = "SEA") -> dict[str, object]:
    return {
        "game_id": game_id,
        "season": 2026,
        "week": 2,
        "season_type": "REG",
        "home_team": home,
        "away_team": "NE",
        "kickoff_at": KICKOFF.isoformat().replace("+00:00", "Z"),
    }


def setup_paths(tmp_path: Path, games: list[dict[str, object]] | None = None):
    schedule = tmp_path / "schedule.json"
    history = tmp_path / "totals.jsonl"
    attempts = tmp_path / "attempts.jsonl"
    schedule.write_text(json.dumps(games or [game()]), encoding="utf-8")
    return schedule, history, attempts


def books(now: datetime):
    stamp = now.isoformat().replace("+00:00", "Z")
    return tuple(
        {
            "bookmaker_key": key,
            "bookmaker": name,
            "total": 47.5,
            "over_price": -110,
            "under_price": -110,
            "observed_at": stamp,
        }
        for key, name in (("betmgm", "BetMGM"), ("fanduel", "FanDuel"), ("draftkings", "DraftKings"))
    )


@pytest.mark.parametrize(
    ("label", "low", "high"),
    [("T12H", 660, 780), ("T6H", 330, 390), ("T3H", 150, 210), ("T1H", 45, 75), ("NEAR_KICKOFF", 5, 30)],
)
def test_frozen_window_boundaries(label: str, low: int, high: int) -> None:
    assert collector.eligible_target(low) == label
    assert collector.eligible_target(low + 0.01) == label
    assert collector.eligible_target(high) == label
    assert collector.eligible_target(high - 0.01) == label
    assert collector.eligible_target(low - 0.01) != label
    assert collector.eligible_target(high + 0.01) != label


@pytest.mark.parametrize("unsafe", [" ", "\n", "\r", "\t", "\0", "\x7f"])
def test_totals_rejects_url_disallowed_api_key(
    monkeypatch: pytest.MonkeyPatch, unsafe: str
) -> None:
    key = f"TEST{unsafe}KEY"
    monkeypatch.setattr(
        collector.game_day,
        "validated_odds_api_key",
        lambda: collector.game_day._validate_odds_api_key(key),
    )
    with pytest.raises(OperationalTotalsError) as error:
        collector.fetch_live_totals_payload()
    assert key not in str(error.value)


def test_totals_url_uses_encoded_frozen_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "TEST_KEY")
    monkeypatch.setattr(
        collector.urllib.request,
        "urlopen",
        lambda request, timeout: captured.append(request.full_url) or Response(),
    )
    monkeypatch.setattr(collector.json, "load", lambda _response: [])
    assert collector.fetch_live_totals_payload() == []
    parsed = urlsplit(captured[0])
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == collector.ODDS_URL
    assert parse_qs(parsed.query) == {
        "apiKey": ["TEST_KEY"],
        "regions": ["us"],
        "markets": ["totals"],
        "oddsFormat": ["american"],
        "bookmakers": ["draftkings,fanduel,betmgm"],
    }


def test_dry_run_and_outside_window_never_fetch_or_write(tmp_path: Path) -> None:
    schedule, history, attempts = setup_paths(tmp_path)
    for minutes, dry_run in ((720, True), (500, False)):
        collector.collect(
            now=KICKOFF - timedelta(minutes=minutes),
            schedule_path=schedule,
            history_path=history,
            attempt_path=attempts,
            dry_run=dry_run,
            fetcher=lambda *_: pytest.fail("provider called"),
        )
    assert not history.exists()
    assert len(read_totals_attempts(attempts)) == 1


def test_success_is_one_fetch_one_history_and_one_attempt(tmp_path: Path) -> None:
    schedule, history, attempts = setup_paths(tmp_path)
    now = KICKOFF - timedelta(minutes=720)
    calls = 0

    def fetch(*_):
        nonlocal calls
        calls += 1
        return books(now)

    collector.collect(now=now, schedule_path=schedule, history_path=history, attempt_path=attempts, fetcher=fetch)
    collector.collect(now=now, schedule_path=schedule, history_path=history, attempt_path=attempts, fetcher=fetch)
    assert calls == 1
    assert len(read_totals_history(history)) == 1
    assert len(read_totals_attempts(attempts)) == 1


def test_provider_failure_isolated_and_writes_attempt_only(tmp_path: Path) -> None:
    games = [game(), game("2026_02_NE_DEN", "DEN")]
    schedule, history, attempts = setup_paths(tmp_path, games)
    now = KICKOFF - timedelta(minutes=720)

    def fetch(selected, _now):
        if selected["home_team"] == "SEA":
            raise OperationalTotalsError("totals provider request failed")
        return books(now)

    rows = collector.collect(now=now, schedule_path=schedule, history_path=history, attempt_path=attempts, fetcher=fetch)
    assert [row["result"] for row in rows] == ["FAILED", "SUCCESS"]
    assert len(read_totals_history(history)) == 1
    assert len(read_totals_attempts(attempts)) == 2


def test_corrupt_retained_state_fails_before_provider(tmp_path: Path) -> None:
    schedule, history, attempts = setup_paths(tmp_path)
    history.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(OperationalTotalsError):
        collector.collect(
            now=KICKOFF - timedelta(minutes=720), schedule_path=schedule,
            history_path=history, attempt_path=attempts,
            fetcher=lambda *_: pytest.fail("provider called"),
        )


def test_orphan_history_recovers_without_refetch(monkeypatch, tmp_path: Path) -> None:
    schedule, history, attempts = setup_paths(tmp_path)
    now = KICKOFF - timedelta(minutes=720)
    real_append = collector.append_totals_attempt
    monkeypatch.setattr(collector, "append_totals_attempt", lambda *_: (_ for _ in ()).throw(OSError("disk")))
    first = collector.collect(now=now, schedule_path=schedule, history_path=history, attempt_path=attempts, fetcher=lambda *_: books(now))
    assert first[-1]["reason"] == "ATTEMPT_LOG_APPEND_FAILED"
    assert len(read_totals_history(history)) == 1
    monkeypatch.setattr(collector, "append_totals_attempt", real_append)
    second = collector.collect(
        now=now, schedule_path=schedule, history_path=history, attempt_path=attempts,
        fetcher=lambda *_: pytest.fail("provider called"),
    )
    assert second[0]["reason"] == "RECOVERED_SUCCESS"
    assert len(read_totals_history(history)) == 1
    assert read_totals_attempts(attempts)[0]["reason_code"] == "RECOVERED_SUCCESS"


def test_history_append_failure_records_bounded_failure(monkeypatch, tmp_path: Path) -> None:
    schedule, history, attempts = setup_paths(tmp_path)
    now = KICKOFF - timedelta(minutes=720)
    monkeypatch.setattr(collector, "append_totals_observation", lambda *_: (_ for _ in ()).throw(OSError("disk")))
    rows = collector.collect(
        now=now, schedule_path=schedule, history_path=history,
        attempt_path=attempts, fetcher=lambda *_: books(now),
    )
    assert rows[-1]["reason"] == "HISTORY_APPEND_FAILED"
    assert not history.exists()
    assert read_totals_attempts(attempts)[0]["reason_code"] == "HISTORY_APPEND_FAILED"


def test_contradictory_automatic_orphans_fail_closed(tmp_path: Path) -> None:
    schedule, history, attempts = setup_paths(tmp_path)
    now = KICKOFF - timedelta(minutes=720)
    first = build_totals_observation(
        game(), books(now), collected_at=now, target_label="T12H",
        provider=AUTOMATIC_PROVIDER_PREFIX + "T12H",
    )
    second = build_totals_observation(
        game(), books(now + timedelta(minutes=1)), collected_at=now + timedelta(minutes=1),
        target_label="T12H", provider=AUTOMATIC_PROVIDER_PREFIX + "T12H",
    )
    history.write_text(canonical_json(first) + "\n" + canonical_json(second) + "\n", encoding="utf-8")
    with pytest.raises(OperationalTotalsError):
        collector.collect(
            now=now, schedule_path=schedule, history_path=history,
            attempt_path=attempts, fetcher=lambda *_: pytest.fail("provider called"),
        )


def test_manual_observation_never_triggers_recovery(tmp_path: Path) -> None:
    schedule, history, attempts = setup_paths(tmp_path)
    now = KICKOFF - timedelta(minutes=720)
    manual = build_totals_observation(game(), books(now), collected_at=now, target_label="MANUAL", provider=MANUAL_PROVIDER)
    append_totals_observation(history, manual)
    rows = collector.collect(
        now=now, schedule_path=schedule, history_path=history, attempt_path=attempts,
        dry_run=True, fetcher=lambda *_: pytest.fail("provider called"),
    )
    assert rows[-1]["result"] == "DRY_RUN_ELIGIBLE"


def test_post_kickoff_never_fetches_or_writes(tmp_path: Path) -> None:
    schedule, history, attempts = setup_paths(tmp_path)
    rows = collector.collect(
        now=KICKOFF + timedelta(seconds=1), schedule_path=schedule,
        history_path=history, attempt_path=attempts,
        fetcher=lambda *_: pytest.fail("provider called"),
    )
    assert rows == ({"game_id": "2026_02_NE_SEA", "target": None, "result": "POST_KICKOFF"},)
    assert not history.exists() and not attempts.exists()
