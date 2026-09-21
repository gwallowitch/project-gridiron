from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from gridiron.market.operational_history import canonical_json
from gridiron.market.operational_spreads import (
    BOOK_KEYS,
    ImmutableSpreadConflictError,
    OperationalSpreadError,
)
from gridiron.market.spread_collection_attempts import (
    SpreadAttemptError,
    build_spread_attempt,
)
from gridiron.market.spread_provider import SpreadParseError, parse_spread_event
from gridiron.market.spread_repository import (
    SpreadEvidenceRepository,
    validate_spread_evidence_set,
)

KICKOFF = datetime(2026, 9, 20, 17, tzinfo=UTC)
COLLECTED = KICKOFF - timedelta(minutes=60)
RAW_ID = "a" * 64
PAYLOAD_SHA = "b" * 64
GAME = {
    "game_id": "2026_02_SEA_SF", "season": 2026, "week": 2,
    "season_type": "REG", "home_team": "SF", "away_team": "SEA",
    "kickoff_at": "2026-09-20T17:00:00Z",
}


def market(
    home: float = -3.5,
    away: float = 3.5,
    home_price: object = -108,
    away_price: object = -112,
    *,
    updated: datetime = COLLECTED - timedelta(minutes=2),
    reverse: bool = False,
) -> dict[str, object]:
    outcomes = [
        {"name": "SF", "point": home, "price": home_price},
        {"name": "SEA", "point": away, "price": away_price},
    ]
    return {
        "key": "spreads", "last_update": updated.isoformat(),
        "outcomes": list(reversed(outcomes)) if reverse else outcomes,
    }


def event(lines: dict[str, tuple[float, float]] | None = None) -> dict[str, object]:
    lines = lines or {key: (-3.5, 3.5) for key in BOOK_KEYS}
    return {
        "id": "provider-event-1", "commence_time": GAME["kickoff_at"],
        "home_team": "SF", "away_team": "SEA",
        "bookmakers": [
            {
                "key": key,
                "last_update": (COLLECTED - timedelta(minutes=5)).isoformat(),
                "markets": [market(*lines[key])],
            }
            for key in BOOK_KEYS
        ],
    }


def parse(
    payload: object | None = None,
    *,
    collected_at: datetime = COLLECTED,
    target: str = "T1H",
    raw_id: str = RAW_ID,
) -> dict[str, object]:
    return parse_spread_event(
        event() if payload is None else payload,
        GAME,
        collected_at=collected_at,
        target_label=target,
        raw_response_id=raw_id,
        raw_payload_sha256=PAYLOAD_SHA,
        expected_provider_event_id="provider-event-1",
    )


def success(observation: dict[str, object], **changes) -> dict[str, object]:
    values = {
        "game_id": observation["game"]["game_id"],
        "target_label": observation["timing"]["target_label"],
        "kickoff_at": observation["game"]["kickoff_at"],
        "attempted_at": datetime.fromisoformat(
            observation["timing"]["collected_at"]
        ),
        "result": "SUCCESS", "reason_code": "SUCCESS",
        "observation_id": observation["observation_id"],
        "raw_response_id": observation["raw_response_id"],
    }
    values.update(changes)
    return build_spread_attempt(**values)


def test_valid_payload_preserves_lines_prices_timestamps_and_raw_linkage() -> None:
    row = parse()
    assert [book["home_price"] for book in row["books"]] == [-108, -108, -108]
    assert row["books"][0]["home_points"] == -3.5
    assert row["books"][0]["bookmaker_last_update"] == "2026-09-20T15:58:00Z"
    assert row["raw_response_id"] == RAW_ID
    assert row["raw_payload_sha256"] == PAYLOAD_SHA


def test_different_main_lines_home_underdog_pickem_and_plus_money() -> None:
    row = parse(event({"betmgm": (-2.5, 2.5), "fanduel": (-3.0, 3.0), "draftkings": (-3.5, 3.5)}))
    assert [book["home_points"] for book in row["books"]] == [-2.5, -3.0, -3.5]
    underdog = event({key: (3.5, -3.5) for key in BOOK_KEYS})
    underdog["bookmakers"][0]["markets"][0]["outcomes"][0]["price"] = 105
    assert parse(underdog)["books"][0]["home_price"] == 105
    pickem = event({key: (-0.0, 0.0) for key in BOOK_KEYS})
    assert all(book["home_points"] == 0.0 for book in parse(pickem)["books"])


def test_outcome_order_is_team_mapped_and_unrelated_book_is_ignored() -> None:
    data = event()
    data["bookmakers"][0]["markets"] = [market(reverse=True)]
    data["bookmakers"].append({"key": "other", "markets": []})
    row = parse(data)
    assert row["books"][0]["home_team"] == "SF"
    assert row["books"][0]["home_points"] == -3.5


def test_market_timestamp_precedes_bookmaker_fallback() -> None:
    data = event()
    data["bookmakers"][0]["last_update"] = (COLLECTED - timedelta(minutes=9)).isoformat()
    data["bookmakers"][0]["markets"][0]["last_update"] = (COLLECTED - timedelta(minutes=1)).isoformat()
    assert parse(data)["books"][0]["bookmaker_last_update"] == "2026-09-20T15:59:00Z"
    data["bookmakers"][0]["markets"][0].pop("last_update")
    assert parse(data)["books"][0]["bookmaker_last_update"] == "2026-09-20T15:51:00Z"


@pytest.mark.parametrize("missing", BOOK_KEYS)
def test_each_required_book_is_mandatory(missing: str) -> None:
    data = event()
    data["bookmakers"] = [book for book in data["bookmakers"] if book["key"] != missing]
    with pytest.raises(SpreadParseError, match="MISSING_BOOK"):
        parse(data)


def test_missing_and_ambiguous_spread_market_fail_closed() -> None:
    missing = event()
    missing["bookmakers"][0]["markets"] = []
    with pytest.raises(SpreadParseError, match="MISSING_MARKET"):
        parse(missing)
    duplicate = event()
    duplicate["bookmakers"][0]["markets"].append(market())
    with pytest.raises(SpreadParseError, match="MALFORMED_MARKET"):
        parse(duplicate)


@pytest.mark.parametrize("field,value", [("home_team", "OTHER"), ("away_team", "OTHER")])
def test_team_identity_mismatch_rejects(field: str, value: str) -> None:
    data = event()
    data[field] = value
    with pytest.raises(SpreadParseError, match="IDENTITY_MISMATCH"):
        parse(data)


def test_reversed_event_kickoff_and_provider_id_mismatch_reject() -> None:
    for mutation in ("reversed", "kickoff", "id"):
        data = event()
        if mutation == "reversed":
            data["home_team"], data["away_team"] = data["away_team"], data["home_team"]
        elif mutation == "kickoff":
            data["commence_time"] = "2026-09-20T18:00:00Z"
        else:
            data["id"] = "wrong"
        with pytest.raises(SpreadParseError, match="IDENTITY_MISMATCH"):
            parse(data)


@pytest.mark.parametrize("case", ["missing_home", "missing_away", "duplicate", "three"])
def test_outcome_cardinality_and_identity_fail_closed(case: str) -> None:
    data = event()
    outcomes = data["bookmakers"][0]["markets"][0]["outcomes"]
    if case == "missing_home":
        outcomes.pop(0)
    elif case == "missing_away":
        outcomes.pop()
    elif case == "duplicate":
        outcomes[1] = deepcopy(outcomes[0])
    else:
        outcomes.append({"name": "OTHER", "point": 0.0, "price": -110})
    with pytest.raises(SpreadParseError, match="MALFORMED_MARKET"):
        parse(data)


@pytest.mark.parametrize("point", [2.5, float("nan"), float("inf")])
def test_conflicting_and_nonfinite_points_reject(point: float) -> None:
    data = event()
    data["bookmakers"][0]["markets"][0]["outcomes"][1]["point"] = point
    code = "CONFLICTING_SPREAD" if point == 2.5 else "MALFORMED_MARKET"
    with pytest.raises(SpreadParseError, match=code):
        parse(data)


@pytest.mark.parametrize("price", [None, 0, 50, -50, -110.5, "-110", float("nan"), float("inf")])
def test_malformed_prices_reject_without_coercion(price: object) -> None:
    data = event()
    data["bookmakers"][0]["markets"][0]["outcomes"][0]["price"] = price
    with pytest.raises(SpreadParseError, match="MALFORMED_MARKET"):
        parse(data)


def test_future_stale_and_invalid_timestamps_map_deterministically() -> None:
    for stamp, code in (
        (COLLECTED + timedelta(seconds=1), "TIMESTAMP_INVALID"),
        (COLLECTED - timedelta(minutes=11), "STALE_QUOTE"),
    ):
        data = event()
        data["bookmakers"][0]["markets"][0]["last_update"] = stamp.isoformat()
        with pytest.raises(SpreadParseError, match=code):
            parse(data)
    data = event()
    data["bookmakers"][0]["markets"][0]["last_update"] = "invalid"
    with pytest.raises(SpreadParseError, match="TIMESTAMP_INVALID"):
        parse(data)


@pytest.mark.parametrize("minutes", [0, -1, 44, 76])
def test_collection_and_target_timing_fail_closed(minutes: int) -> None:
    with pytest.raises(SpreadParseError, match="TIMESTAMP_INVALID"):
        parse(collected_at=KICKOFF - timedelta(minutes=minutes))
    with pytest.raises(SpreadParseError, match="MALFORMED_MARKET"):
        parse(target="OTHER")


@pytest.mark.parametrize("payload", [[], [{"id": "one"}, {"id": "two"}], "bad"])
def test_event_boundary_rejects_missing_malformed_or_multi_event_payload(payload: object) -> None:
    with pytest.raises(SpreadParseError, match="MISSING_GAME|MALFORMED_MARKET"):
        parse(payload)
    with pytest.raises(SpreadParseError, match="MISSING_GAME"):
        parse_spread_event(
            None, GAME, collected_at=COLLECTED, target_label="T1H",
            raw_response_id=RAW_ID, raw_payload_sha256=PAYLOAD_SHA,
        )


def test_failure_is_sanitized_and_never_echoes_payload() -> None:
    secret = "authorization=Bearer-super-secret"
    data = event()
    data["home_team"] = secret
    with pytest.raises(SpreadParseError) as captured:
        parse(data)
    assert str(captured.value) == "IDENTITY_MISMATCH"
    assert secret not in str(captured.value)


def test_parser_exact_replay_and_raw_mutation_identity() -> None:
    first = parse()
    assert parse() == first
    changed = parse(raw_id="c" * 64)
    assert changed["observation_id"] != first["observation_id"]


def test_repository_round_trip_replay_conflict_and_no_rewrite(tmp_path: Path) -> None:
    repository = SpreadEvidenceRepository(tmp_path / "observations.jsonl", tmp_path / "attempts.jsonl")
    observed = parse()
    assert repository.append_observation(observed) is True
    before = repository.observation_path.read_bytes()
    assert repository.append_observation(observed) is False
    assert repository.observation_path.read_bytes() == before
    assert repository.observations() == (observed,)
    with pytest.raises(ImmutableSpreadConflictError):
        repository.append_observation(parse(raw_id="c" * 64))
    assert repository.observation_path.read_bytes() == before


def test_different_target_slots_and_multiple_attempt_slots_are_valid(tmp_path: Path) -> None:
    repository = SpreadEvidenceRepository(tmp_path / "observations.jsonl", tmp_path / "attempts.jsonl")
    one = parse()
    six_hours = KICKOFF - timedelta(minutes=360)
    data = event()
    for book in data["bookmakers"]:
        book["last_update"] = (six_hours - timedelta(minutes=2)).isoformat()
        book["markets"][0]["last_update"] = (six_hours - timedelta(minutes=2)).isoformat()
    two = parse(data, collected_at=six_hours, target="T6H")
    assert repository.append_observation(one)
    assert repository.append_observation(two)
    assert repository.append_attempt(success(one))
    assert repository.append_attempt(success(two))
    repository.validate()


def test_success_requires_existing_exact_observation(tmp_path: Path) -> None:
    repository = SpreadEvidenceRepository(tmp_path / "observations.jsonl", tmp_path / "attempts.jsonl")
    observed = parse()
    with pytest.raises(SpreadAttemptError, match="missing observation"):
        repository.append_attempt(success(observed))
    repository.append_observation(observed)
    for change in (
        {"game_id": "other"}, {"raw_response_id": "c" * 64},
        {"kickoff_at": "2026-09-20T18:00:00Z", "attempted_at": datetime(2026, 9, 20, 17, tzinfo=UTC)},
    ):
        with pytest.raises(SpreadAttemptError, match="missing observation|inconsistent"):
            repository.append_attempt(success(observed, **change))


def test_failed_attempt_needs_no_observation_and_cannot_fabricate_one(tmp_path: Path) -> None:
    repository = SpreadEvidenceRepository(tmp_path / "observations.jsonl", tmp_path / "attempts.jsonl")
    failed = build_spread_attempt(
        game_id=GAME["game_id"], target_label="T1H", kickoff_at=GAME["kickoff_at"],
        attempted_at=COLLECTED, result="FAILED", reason_code="MISSING_BOOK",
        raw_response_id=RAW_ID,
    )
    assert repository.append_attempt(failed)
    repository.validate()
    with pytest.raises(SpreadAttemptError, match="cannot link observation"):
        build_spread_attempt(
            game_id=GAME["game_id"], target_label="T1H", kickoff_at=GAME["kickoff_at"],
            attempted_at=COLLECTED, result="FAILED", reason_code="MISSING_BOOK",
            observation_id="d" * 64, raw_response_id=RAW_ID,
        )


def test_attempt_replay_conflict_and_cross_validation(tmp_path: Path) -> None:
    repository = SpreadEvidenceRepository(tmp_path / "observations.jsonl", tmp_path / "attempts.jsonl")
    observed = parse()
    linked = success(observed)
    repository.append_observation(observed)
    assert repository.append_attempt(linked)
    before = repository.attempt_path.read_bytes()
    assert repository.append_attempt(linked) is False
    assert repository.attempt_path.read_bytes() == before
    conflicting = build_spread_attempt(
        game_id=GAME["game_id"], target_label="T1H", kickoff_at=GAME["kickoff_at"],
        attempted_at=COLLECTED, result="FAILED", reason_code="MISSING_MARKET",
        raw_response_id=RAW_ID,
    )
    with pytest.raises(ImmutableSpreadConflictError):
        repository.append_attempt(conflicting)
    validate_spread_evidence_set((observed,), (linked,))
    with pytest.raises(SpreadAttemptError, match="missing observation"):
        validate_spread_evidence_set((), (linked,))


@pytest.mark.parametrize("kind", ["malformed", "truncated", "bad_identity", "negative_zero"])
def test_malformed_existing_observation_fails_closed(tmp_path: Path, kind: str) -> None:
    repository = SpreadEvidenceRepository(tmp_path / "observations.jsonl", tmp_path / "attempts.jsonl")
    if kind == "malformed":
        text = "not-json\n"
    elif kind == "truncated":
        text = '{"schema_version":1'
    else:
        row = parse()
        if kind == "bad_identity":
            row["observation_id"] = "0" * 64
        else:
            row["books"][0]["home_points"] = -0.0
        text = canonical_json(row) + "\n"
    repository.observation_path.write_text(text, encoding="utf-8")
    with pytest.raises(OperationalSpreadError):
        repository.observations()


def test_malformed_existing_attempt_fails_closed(tmp_path: Path) -> None:
    repository = SpreadEvidenceRepository(tmp_path / "observations.jsonl", tmp_path / "attempts.jsonl")
    repository.attempt_path.write_text("{\"truncated\":", encoding="utf-8")
    with pytest.raises(SpreadAttemptError):
        repository.attempts()


def test_write_failure_does_not_claim_success(tmp_path: Path) -> None:
    directory = tmp_path / "is-a-directory"
    directory.mkdir()
    repository = SpreadEvidenceRepository(directory, tmp_path / "attempts.jsonl")
    with pytest.raises(OSError):
        repository.append_observation(parse())
    assert directory.is_dir()
