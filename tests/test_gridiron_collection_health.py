from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from gridiron.market.collection_attempts import (
    append_collection_attempt,
    build_collection_attempt,
)
from gridiron.market.operational_totals import (
    AUTOMATIC_PROVIDER_PREFIX,
    append_totals_observation,
    build_totals_observation,
)
from gridiron.market.totals_collection_attempts import (
    append_totals_attempt,
    build_totals_attempt,
)
from scripts import gridiron_collection_health as health
from scripts import gridiron_market_collector as moneyline_collector

KICKOFF = datetime(2026, 9, 20, 17, tzinfo=UTC)
GAME = {
    "game_id": "2026_02_NE_SEA", "season": 2026, "week": 2,
    "season_type": "REG", "home_team": "SEA", "away_team": "NE",
    "kickoff_at": KICKOFF.isoformat().replace("+00:00", "Z"),
}
PRICES = {"BetMGM": (-175, 145), "FanDuel": (-176, 146), "DraftKings": (-177, 147)}


def paths(tmp_path: Path) -> dict[str, Path]:
    result = {
        "schedule": tmp_path / "schedule.json",
        "mh": tmp_path / "moneyline.jsonl",
        "ma": tmp_path / "moneyline-attempts.jsonl",
        "th": tmp_path / "totals.jsonl",
        "ta": tmp_path / "totals-attempts.jsonl",
    }
    result["schedule"].write_text(json.dumps([GAME]), encoding="utf-8")
    return result


def audit(p: dict[str, Path], now: datetime, **kwargs):
    return health.audit_collection_health(
        as_of=now, schedule_path=p["schedule"],
        moneyline_history_path=p["mh"], moneyline_attempt_path=p["ma"],
        totals_history_path=p["th"], totals_attempt_path=p["ta"],
        game_id=GAME["game_id"], **kwargs,
    )["games"][0]


def add_moneyline_attempt(p, label, minutes, result, reason, observation_id=None):
    row = build_collection_attempt(
        game_id=GAME["game_id"], collection_target=label,
        target_minutes_to_kickoff=health.WINDOW_BY_TARGET[label][0],
        kickoff_at=GAME["kickoff_at"], attempted_at=KICKOFF - timedelta(minutes=minutes),
        result=result, reason_code=reason, observation_id=observation_id,
    )
    append_collection_attempt(p["ma"], row)


def add_totals_attempt(p, label, minutes, result, reason, observation_id=None):
    row = build_totals_attempt(
        game_id=GAME["game_id"], target_label=label, kickoff_at=GAME["kickoff_at"],
        attempted_at=KICKOFF - timedelta(minutes=minutes), result=result,
        reason_code=reason, observation_id=observation_id,
    )
    append_totals_attempt(p["ta"], row)


def totals_observation(label="T12H", minutes=720):
    stamp = (KICKOFF - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")
    books = tuple(
        {"bookmaker_key": key, "bookmaker": name, "total": 47.5,
         "over_price": -110, "under_price": -110, "observed_at": stamp}
        for key, name in (("betmgm", "BetMGM"), ("fanduel", "FanDuel"), ("draftkings", "DraftKings"))
    )
    return build_totals_observation(
        GAME, books, collected_at=KICKOFF - timedelta(minutes=minutes),
        target_label=label, provider=AUTOMATIC_PROVIDER_PREFIX + label,
    )


def add_moneyline_success(p, label="T12H", minutes=720):
    now = KICKOFF - timedelta(minutes=minutes)
    moneyline_collector.collect(
        now=now, schedule_path=p["schedule"], history_path=p["mh"],
        attempt_path=p["ma"], game_id=GAME["game_id"],
        price_fetcher=lambda _game: (
            PRICES, {book: now.isoformat().replace("+00:00", "Z") for book in PRICES}
        ), def_epa_loader=lambda _game: 0.0,
    )


def add_totals_success(p, label="T12H", minutes=720, attempt=True):
    row = totals_observation(label, minutes)
    append_totals_observation(p["th"], row)
    if attempt:
        add_totals_attempt(p, label, minutes, "SUCCESS", "SUCCESS", row["observation_id"])


def test_all_targets_future_is_not_yet_active(tmp_path: Path) -> None:
    report = audit(paths(tmp_path), KICKOFF - timedelta(minutes=900))
    assert report["moneyline"]["overall"] == "NOT_YET_ACTIVE"
    assert {item["state"] for item in report["moneyline"]["targets"].values()} == {
        "NOT_YET_DUE"
    }


@pytest.mark.parametrize("lane", ["moneyline", "totals"])
def test_current_window_without_attempt_is_due_now(tmp_path: Path, lane: str) -> None:
    report = audit(paths(tmp_path), KICKOFF - timedelta(minutes=720))
    assert report[lane]["overall"] == "ACTION_NEEDED"
    assert report[lane]["targets"]["T12H"] == {"state": "IN_WINDOW_PENDING", "reason": "NO_ATTEMPT_OBSERVED"}


def test_valid_successes_are_independent_and_linked(tmp_path: Path) -> None:
    p = paths(tmp_path)
    add_moneyline_success(p)
    report = audit(p, KICKOFF - timedelta(minutes=700))
    assert report["moneyline"]["targets"]["T12H"]["state"] == "SUCCESS"
    assert report["totals"]["targets"]["T12H"]["state"] == "IN_WINDOW_PENDING"
    add_totals_success(p)
    report = audit(p, KICKOFF - timedelta(minutes=700))
    assert report["totals"]["targets"]["T12H"]["state"] == "SUCCESS"


def test_one_lane_can_be_healthy_while_other_is_degraded(tmp_path: Path) -> None:
    p = paths(tmp_path)
    add_moneyline_success(p)
    add_totals_attempt(p, "T12H", 720, "FAILED", "PROVIDER_ERROR")
    report = audit(p, KICKOFF - timedelta(minutes=700))
    assert report["moneyline"]["overall"] == "HEALTHY"
    assert report["totals"]["overall"] == "DEGRADED"


@pytest.mark.parametrize(
    "lane,reason",
    [("moneyline", "ODDS_PROVIDER_ERROR"), ("totals", "PROVIDER_ERROR")],
)
def test_provider_failure_is_not_missing_attempt(tmp_path: Path, lane: str, reason: str) -> None:
    p = paths(tmp_path)
    if lane == "moneyline":
        add_moneyline_attempt(p, "T12H", 720, "FAILED", reason)
    else:
        add_totals_attempt(p, "T12H", 720, "FAILED", reason)
    state = audit(p, KICKOFF - timedelta(minutes=700))[lane]["targets"]["T12H"]
    assert state == {"state": "FAILED_IN_WINDOW", "reason": reason}


@pytest.mark.parametrize("lane", ["moneyline", "totals"])
def test_explicit_missed_window_is_preserved(tmp_path: Path, lane: str) -> None:
    p = paths(tmp_path)
    if lane == "moneyline":
        add_moneyline_attempt(p, "T12H", 500, "SKIPPED_OUTSIDE_WINDOW", "MISSED_WINDOW")
    else:
        add_totals_attempt(p, "T12H", 500, "MISSED_WINDOW", "MISSED_WINDOW")
    assert audit(p, KICKOFF - timedelta(minutes=500))[lane]["targets"]["T12H"]["state"] == "MISSED_WINDOW"


@pytest.mark.parametrize(
    "minutes,state",
    [(500, "WINDOW_EXPIRED_NO_SUCCESS"), (-1, "POST_KICKOFF_NO_SUCCESS")],
)
def test_no_attempt_expiry_and_post_kickoff_are_explicit(tmp_path: Path, minutes: int, state: str) -> None:
    report = audit(paths(tmp_path), KICKOFF - timedelta(minutes=minutes))
    assert report["moneyline"]["targets"]["T12H"]["state"] == state


def test_orphan_observation_is_recovery_required(tmp_path: Path) -> None:
    p = paths(tmp_path)
    add_totals_success(p, attempt=False)
    report = audit(p, KICKOFF - timedelta(minutes=700))
    assert report["totals"]["overall"] == "ACTION_NEEDED"
    assert report["totals"]["targets"]["T12H"]["state"] == "RECOVERY_REQUIRED"


@pytest.mark.parametrize("minutes", [500, -1])
def test_out_of_window_and_post_kickoff_observation_cannot_cover_target(
    minutes: int,
) -> None:
    row = {
        "provider": health.MONEYLINE_PROVIDER_PREFIX + "T12H",
        "game": {"game_id": GAME["game_id"]},
        "timing": {"minutes_to_kickoff": minutes},
    }
    with pytest.raises(health.CollectionHealthError, match="outside"):
        health._automatic_observations((row,), prefix=health.MONEYLINE_PROVIDER_PREFIX, totals=False)


def test_canonical_matchup_mismatch_fails_closed() -> None:
    observation = {
        "game": {**GAME, "home_team": "BUF"},
        "timing": {"collected_at": "2026-09-20T05:00:00Z"},
    }
    lane = health.LaneEvidence({(GAME["game_id"], "T12H"): observation}, {})
    with pytest.raises(health.CollectionHealthError, match="home_team"):
        health._validate_canonical_evidence((GAME,), lane)


@pytest.mark.parametrize("content", ["not json\n", "{}\n", "\n"])
def test_malformed_history_fails_closed(tmp_path: Path, content: str) -> None:
    p = paths(tmp_path)
    p["mh"].write_text(content, encoding="utf-8")
    with pytest.raises(health.CollectionHealthError):
        audit(p, KICKOFF)


def test_success_attempt_without_history_fails_closed(tmp_path: Path) -> None:
    p = paths(tmp_path)
    add_moneyline_attempt(p, "T12H", 720, "SUCCESS", "SUCCESS", "a" * 64)
    with pytest.raises(health.CollectionHealthError, match="lacks"):
        audit(p, KICKOFF - timedelta(minutes=700))


def test_complete_target_coverage_becomes_game_complete(tmp_path: Path) -> None:
    p = paths(tmp_path)
    for label in health.TARGET_ORDER:
        minutes = health.WINDOW_BY_TARGET[label][0]
        add_moneyline_success(p, label, minutes)
        add_totals_success(p, label, minutes)
    report = audit(p, KICKOFF + timedelta(minutes=1))
    assert report["moneyline"]["overall"] == "GAME_COMPLETE"
    assert report["totals"]["overall"] == "GAME_COMPLETE"


def test_unknown_game_and_invalid_schedule_fail_closed(tmp_path: Path) -> None:
    p = paths(tmp_path)
    with pytest.raises(health.CollectionHealthError, match="not found"):
        health.audit_collection_health(
            as_of=KICKOFF, schedule_path=p["schedule"],
            moneyline_history_path=p["mh"], moneyline_attempt_path=p["ma"],
            totals_history_path=p["th"], totals_attempt_path=p["ta"], game_id="UNKNOWN",
        )
    p["schedule"].write_text(json.dumps([{**GAME, "home_team": None}]), encoding="utf-8")
    with pytest.raises(health.CollectionHealthError):
        audit(p, KICKOFF)


def test_as_of_is_deterministic_and_audit_is_byte_identical(tmp_path: Path) -> None:
    p = paths(tmp_path)
    add_moneyline_attempt(p, "T12H", 720, "FAILED", "ODDS_PROVIDER_ERROR")
    before = {
        key: path.read_bytes() if path.exists() else None for key, path in p.items()
    }
    first = audit(p, KICKOFF - timedelta(minutes=700))
    second = audit(p, KICKOFF - timedelta(minutes=700))
    assert first == second
    assert before == {
        key: path.read_bytes() if path.exists() else None for key, path in p.items()
    }


def test_as_of_excludes_later_attempts_and_observations(tmp_path: Path) -> None:
    p = paths(tmp_path)
    add_moneyline_success(p)
    report = audit(p, KICKOFF - timedelta(minutes=750))
    assert report["moneyline"]["targets"]["T12H"]["state"] == "IN_WINDOW_PENDING"


def test_upcoming_filter_and_json_cli_exit_codes(tmp_path: Path, capsys) -> None:
    p = paths(tmp_path)
    common = ["--schedule", str(p["schedule"]), "--moneyline-history", str(p["mh"]),
              "--moneyline-attempts", str(p["ma"]), "--totals-history", str(p["th"]),
              "--totals-attempts", str(p["ta"]), "--as-of", "2026-09-20T05:00:00Z", "--json"]
    assert health.main(common) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["read_only"] is True and output["odds_fetch"] is False
    assert health.main(common + ["--hours", "0"]) == 0


def test_den_kc_pattern_remains_failed_success_missed(tmp_path: Path) -> None:
    p = paths(tmp_path)
    add_moneyline_attempt(p, "T12H", 687.09, "FAILED", "ODDS_PROVIDER_ERROR")
    # The known successful row is represented by an equivalent valid fixture.
    add_moneyline_success(p, "T6H", 385.609)
    add_moneyline_attempt(p, "T3H", 28.656, "SKIPPED_OUTSIDE_WINDOW", "MISSED_WINDOW")
    add_moneyline_attempt(p, "T1H", 28.656, "SKIPPED_OUTSIDE_WINDOW", "MISSED_WINDOW")
    add_moneyline_attempt(p, "NEAR_KICKOFF", 28.656, "FAILED", "ODDS_PROVIDER_ERROR")
    states = audit(p, KICKOFF - timedelta(minutes=20))["moneyline"]["targets"]
    assert [states[label]["state"] for label in health.TARGET_ORDER] == [
        "FAILED_IN_WINDOW", "SUCCESS", "MISSED_WINDOW", "MISSED_WINDOW", "FAILED_IN_WINDOW"
    ]


def test_audit_does_not_call_prediction_or_provider(tmp_path: Path, monkeypatch) -> None:
    p = paths(tmp_path)
    monkeypatch.setattr(moneyline_collector, "collect", lambda **_kwargs: pytest.fail("collector called"))
    monkeypatch.setattr(moneyline_collector, "game_day", pytest.fail, raising=False)
    report = audit(p, KICKOFF - timedelta(minutes=900))
    assert report["moneyline"]["overall"] == "NOT_YET_ACTIVE"


@pytest.mark.parametrize("lane", ["moneyline", "totals"])
@pytest.mark.parametrize("target", list(health.TARGET_ORDER))
def test_future_windows_never_count_as_missing(tmp_path: Path, lane: str, target: str) -> None:
    report = audit(paths(tmp_path), KICKOFF - timedelta(minutes=900))
    assert report[lane]["targets"][target]["state"] == "NOT_YET_DUE"
