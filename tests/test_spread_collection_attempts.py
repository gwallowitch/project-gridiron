from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from gridiron.market.operational_spreads import (
    BOOK_KEYS,
    ImmutableSpreadConflictError,
    build_spread_observation,
)
from gridiron.market.spread_collection_attempts import (
    FAILURE_REASONS,
    SpreadAttemptError,
    append_spread_attempt,
    build_spread_attempt,
    read_spread_attempts,
    validate_spread_attempt,
    validate_spread_success_linkage,
)

KICKOFF = datetime(2026, 9, 20, 17, tzinfo=UTC)
ATTEMPTED = KICKOFF - timedelta(minutes=60)
OBSERVATION_ID = "c" * 64
RAW_ID = "a" * 64


def attempt(**changes):
    values = {
        "game_id": "2026_02_SEA_SF",
        "target_label": "T1H",
        "kickoff_at": "2026-09-20T17:00:00Z",
        "attempted_at": ATTEMPTED,
        "result": "SUCCESS",
        "reason_code": "SUCCESS",
        "observation_id": OBSERVATION_ID,
        "raw_response_id": RAW_ID,
    }
    values.update(changes)
    return build_spread_attempt(**values)


def test_success_attempt_binds_lane_observation_and_raw_response() -> None:
    row = attempt()
    validate_spread_attempt(row)
    assert row["lane"] == "SPREAD"
    assert row["observation_id"] == OBSERVATION_ID
    assert row["raw_response_id"] == RAW_ID


def test_success_linkage_is_anchored_to_observation_game_target_kickoff_and_raw() -> None:
    observed = build_spread_observation(
        {
            "game_id": "2026_02_SEA_SF", "season": 2026, "week": 2,
            "season_type": "REG", "home_team": "SF", "away_team": "SEA",
            "kickoff_at": "2026-09-20T17:00:00Z",
        },
        [
            {
                "bookmaker_key": key,
                "canonical_bookmaker": {
                    "betmgm": "BetMGM", "fanduel": "FanDuel",
                    "draftkings": "DraftKings",
                }[key],
                "bookmaker_last_update": "2026-09-20T15:58:00Z",
                "market_key": "spreads", "home_team": "SF", "home_points": -3.5,
                "home_price": -110, "away_team": "SEA", "away_points": 3.5,
                "away_price": -110,
            }
            for key in BOOK_KEYS
        ],
        collected_at=ATTEMPTED, target_label="T1H", provider="the-odds-api",
        provider_event_id="provider-event-1", raw_response_id=RAW_ID,
        raw_payload_sha256="b" * 64, parser_version="step92b-v1",
    )
    row = attempt(observation_id=observed["observation_id"])
    validate_spread_success_linkage(observed, row)
    conflicts = (
        attempt(game_id="other-game", observation_id=observed["observation_id"]),
        attempt(raw_response_id="d" * 64, observation_id=observed["observation_id"]),
        attempt(
            kickoff_at="2026-09-20T18:00:00Z",
            attempted_at=datetime(2026, 9, 20, 17, tzinfo=UTC),
            observation_id=observed["observation_id"],
        ),
    )
    for malformed in conflicts:
        with pytest.raises(SpreadAttemptError, match="linkage is inconsistent"):
            validate_spread_success_linkage(observed, malformed)


@pytest.mark.parametrize("reason", sorted(FAILURE_REASONS))
def test_each_failure_reason_creates_no_observation(reason: str) -> None:
    raw = None if reason in {"PROVIDER_FAILURE", "MISSING_GAME"} else RAW_ID
    row = attempt(
        result="FAILED", reason_code=reason, observation_id=None, raw_response_id=raw
    )
    assert row["observation_id"] is None


def test_missed_window_and_post_kickoff_are_representable() -> None:
    missed = attempt(
        attempted_at=KICKOFF - timedelta(minutes=40), result="MISSED_WINDOW",
        reason_code="MISSED_WINDOW", observation_id=None, raw_response_id=None,
    )
    post = attempt(
        attempted_at=KICKOFF, result="POST_KICKOFF", reason_code="POST_KICKOFF",
        observation_id=None, raw_response_id=None,
    )
    validate_spread_attempt(missed)
    validate_spread_attempt(post)


def test_success_without_observation_or_raw_link_rejects() -> None:
    with pytest.raises(SpreadAttemptError, match="observation linkage"):
        attempt(observation_id=None)
    with pytest.raises(SpreadAttemptError, match="raw linkage"):
        attempt(raw_response_id=None)


def test_failure_with_fabricated_observation_rejects() -> None:
    with pytest.raises(SpreadAttemptError, match="cannot link observation"):
        attempt(result="FAILED", reason_code="MALFORMED_MARKET")


def test_invalid_target_and_success_outside_window_reject() -> None:
    with pytest.raises(SpreadAttemptError, match="target"):
        attempt(target_label="OTHER")
    with pytest.raises(SpreadAttemptError, match="outside target"):
        attempt(attempted_at=KICKOFF - timedelta(minutes=40))


def test_attempt_exact_replay_is_idempotent_and_conflict_fails(tmp_path) -> None:
    path = tmp_path / "spread_attempts.jsonl"
    row = attempt()
    assert append_spread_attempt(path, row) is True
    assert append_spread_attempt(path, row) is False
    assert read_spread_attempts(path) == (row,)
    conflict = attempt(
        result="FAILED", reason_code="MISSING_BOOK", observation_id=None,
        raw_response_id=RAW_ID,
    )
    with pytest.raises(ImmutableSpreadConflictError):
        append_spread_attempt(path, conflict)


def test_malformed_raw_identity_rejects() -> None:
    with pytest.raises(SpreadAttemptError, match="raw_response_id"):
        attempt(raw_response_id="bad")
