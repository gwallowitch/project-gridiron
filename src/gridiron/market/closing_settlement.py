"""Non-prospective closing-line, execution, settlement, and CLV contracts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gridiron.market.moneyline import (
    american_odds_to_implied_probability,
    remove_two_sided_vig,
)
from gridiron.market.operational_history import canonical_json, read_operational_history

CLOSE_CLASSIFICATION = "NON_PROSPECTIVE_CLOSING_LINE_OBSERVATION"
EXECUTION_CLASSIFICATION = "NON_PROSPECTIVE_RECORDED_EXECUTION"
FINAL_RESULT_CLASSIFICATION = "NON_PROSPECTIVE_FINAL_RESULT_INPUT"
SETTLEMENT_CLASSIFICATION = "NON_PROSPECTIVE_EXECUTION_SETTLEMENT"
BOOKS = ("BetMGM", "FanDuel", "DraftKings")
FUNDING_TYPES = ("CASH", "BONUS_BET")
GAME_ID_PATTERN = re.compile(r"^2026_(?:0[1-9]|1[0-6])_[A-Z0-9]+_[A-Z0-9]+$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ClosingSettlementError(ValueError):
    """An observational audit object is unavailable, corrupt, or inconsistent."""


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ClosingSettlementError(f"{field} must be an ISO-8601 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ClosingSettlementError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ClosingSettlementError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _utc_text(value: object, field: str) -> str:
    return _timestamp(value, field).isoformat().replace("+00:00", "Z")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClosingSettlementError(f"{field} must be non-empty text")
    return value


def _odds(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or -100 < value < 100:
        raise ClosingSettlementError(f"{field} must be integer American odds")
    return value


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClosingSettlementError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ClosingSettlementError(f"{field} must be finite")
    return result


def _identity(base: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(base).encode("utf-8")).hexdigest()


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ClosingSettlementError(f"{field} must be an object")
    return value


def _game_id(value: object) -> str:
    text = _text(value, "game_id")
    if GAME_ID_PATTERN.fullmatch(text) is None:
        raise ClosingSettlementError("game_id must be canonical 2026 REG Week 1-16 identity")
    return text


def _sha256(value: object, field: str) -> str:
    text = _text(value, field)
    if SHA256_PATTERN.fullmatch(text) is None:
        raise ClosingSettlementError(f"{field} must be a lowercase SHA256 identity")
    return text


def select_closing_observation(
    observations: Sequence[Mapping[str, Any]], game_id: str
) -> Mapping[str, Any] | None:
    """Select the latest actual valid pre-kickoff observation for one game."""
    eligible = []
    for row in observations:
        game = row.get("game")
        timing = row.get("timing")
        if not isinstance(game, Mapping) or not isinstance(timing, Mapping):
            continue
        if game.get("game_id") != game_id:
            continue
        collected = _timestamp(timing.get("collected_at"), "collected_at")
        kickoff = _timestamp(game.get("kickoff_at"), "kickoff_at")
        if collected < kickoff:
            eligible.append((collected, row))
    if not eligible:
        return None
    latest = max(item[0] for item in eligible)
    winners = [row for collected, row in eligible if collected == latest]
    identities = {row.get("observation_id") for row in winners}
    if len(winners) != 1 or len(identities) != 1:
        raise ClosingSettlementError("contradictory observations share latest timestamp")
    return winners[0]


def build_closing_line(observation: Mapping[str, Any]) -> dict[str, Any]:
    game = observation["game"]
    timing = observation["timing"]
    collected = _timestamp(timing["collected_at"], "collected_at")
    kickoff = _timestamp(game["kickoff_at"], "kickoff_at")
    if collected >= kickoff:
        raise ClosingSettlementError("closing observation must be pre-kickoff")
    by_book = {book["book"]: book for book in observation["books"]}
    if set(by_book) != set(BOOKS):
        raise ClosingSettlementError("closing observation requires three books")
    books = {}
    fair_home = []
    for name in BOOKS:
        home = _odds(by_book[name]["home_odds"], f"{name} home odds")
        away = _odds(by_book[name]["away_odds"], f"{name} away odds")
        fair = remove_two_sided_vig(home, away)
        fair_home.append(fair.home_fair_probability)
        books[name] = {"home_odds": home, "away_odds": away}
    expected_home = sum(fair_home) / len(fair_home)
    market = _mapping(observation.get("market"), "market")
    consensus_home = _number(market.get("home_probability"), "market.home_probability")
    consensus_away = _number(market.get("away_probability"), "market.away_probability")
    if not math.isclose(consensus_home, expected_home, abs_tol=1e-12) or not math.isclose(
        consensus_away, 1.0 - expected_home, abs_tol=1e-12
    ):
        raise ClosingSettlementError("stored closing consensus is inconsistent")
    dk = books["DraftKings"]
    base = {
        "schema_version": 1,
        "record_type": "CLOSING_LINE_OBSERVATION",
        "classification": CLOSE_CLASSIFICATION,
        "prospective_evidence": False,
        "game_id": _game_id(game["game_id"]),
        "kickoff_at": _utc_text(game["kickoff_at"], "kickoff_at"),
        "closing_observation_id": _sha256(observation["observation_id"], "closing_observation_id"),
        "closing_collected_at": _utc_text(timing["collected_at"], "collected_at"),
        "minutes_before_kickoff": (kickoff - collected).total_seconds() / 60.0,
        "provider": observation["provider"],
        "books": books,
        "consensus_home_probability": consensus_home,
        "consensus_away_probability": consensus_away,
        "draftkings_home_break_even_probability": american_odds_to_implied_probability(dk["home_odds"]),
        "draftkings_away_break_even_probability": american_odds_to_implied_probability(dk["away_odds"]),
    }
    return {**base, "closing_line_id": _identity(base)}


def closing_line_from_history(path: Path | str, game_id: str) -> dict[str, Any] | None:
    """Read hardened Step 91P history and derive one deterministic close."""
    selected = select_closing_observation(read_operational_history(path), game_id)
    return None if selected is None else build_closing_line(selected)


def build_execution(
    *, game_id: str, kickoff_at: str, executed_at: str, side: str,
    american_odds: int, stake: float, currency: str, source_book: str,
    related_observation_id: str | None = None,
    funding_type: str | None = "CASH",
) -> dict[str, Any]:
    kickoff = _timestamp(kickoff_at, "kickoff_at")
    executed = _timestamp(executed_at, "executed_at")
    if executed >= kickoff:
        raise ClosingSettlementError("execution must be strictly pre-kickoff")
    if side not in {"HOME", "AWAY"}:
        raise ClosingSettlementError("execution side must be HOME or AWAY")
    amount = _number(stake, "stake")
    if amount <= 0:
        raise ClosingSettlementError("stake must be positive")
    if related_observation_id is not None:
        related_observation_id = _sha256(
            related_observation_id, "related_observation_id"
        )
    currency_text = _text(currency, "currency").upper()
    if len(currency_text) != 3 or not currency_text.isalpha():
        raise ClosingSettlementError("currency must be a three-letter code")
    if funding_type is not None and funding_type not in FUNDING_TYPES:
        raise ClosingSettlementError("funding_type must be CASH or BONUS_BET")
    base = {
        "schema_version": 1 if funding_type is None else 2,
        "record_type": "RECORDED_EXECUTION",
        "classification": EXECUTION_CLASSIFICATION,
        "prospective_evidence": False,
        "game_id": _game_id(game_id),
        "kickoff_at": _utc_text(kickoff_at, "kickoff_at"),
        "executed_at": _utc_text(executed_at, "executed_at"),
        "side": side,
        "american_odds": _odds(american_odds, "american_odds"),
        "stake": amount,
        "currency": currency_text,
        "source_book": _text(source_book, "source_book"),
        "related_observation_id": related_observation_id,
    }
    if funding_type is not None:
        base["funding_type"] = funding_type
    return {**base, "execution_id": _identity(base)}


def build_final_result(
    *, game_id: str, status: str, home_score: int, away_score: int,
    source: str, acquired_at: str,
) -> dict[str, Any]:
    if status != "FINAL":
        raise ClosingSettlementError("only FINAL game results are accepted")
    for value, field in ((home_score, "home_score"), (away_score, "away_score")):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ClosingSettlementError(f"{field} must be a nonnegative integer")
    base = {
        "schema_version": 1,
        "record_type": "FINAL_RESULT_INPUT",
        "classification": FINAL_RESULT_CLASSIFICATION,
        "game_id": _game_id(game_id),
        "status": status,
        "home_score": home_score,
        "away_score": away_score,
        "source": _text(source, "source"),
        "acquired_at": _utc_text(acquired_at, "acquired_at"),
    }
    return {**base, "final_result_id": _identity(base)}


def _validate_identity(record: Mapping[str, Any], identity_field: str) -> None:
    material = dict(record)
    identity = material.pop(identity_field, None)
    if identity != _identity(material):
        raise ClosingSettlementError(f"invalid {identity_field}")


def validate_execution(record: Mapping[str, Any]) -> None:
    _validate_identity(record, "execution_id")
    schema_version = record.get("schema_version")
    if schema_version not in {1, 2}:
        raise ClosingSettlementError("unsupported execution schema_version")
    expected = build_execution(
        game_id=record.get("game_id"), kickoff_at=record.get("kickoff_at"),
        executed_at=record.get("executed_at"), side=record.get("side"),
        american_odds=record.get("american_odds"), stake=record.get("stake"),
        currency=record.get("currency"), source_book=record.get("source_book"),
        related_observation_id=record.get("related_observation_id"),
        funding_type=None if schema_version == 1 else record.get("funding_type"),
    )
    if dict(record) != expected:
        raise ClosingSettlementError("execution fields or semantics are invalid")


def validate_final_result(record: Mapping[str, Any]) -> None:
    _validate_identity(record, "final_result_id")
    expected = build_final_result(
        game_id=record.get("game_id"), status=record.get("status"),
        home_score=record.get("home_score"), away_score=record.get("away_score"),
        source=record.get("source"), acquired_at=record.get("acquired_at"),
    )
    if dict(record) != expected:
        raise ClosingSettlementError("final-result fields or semantics are invalid")


def _profit(stake: float, odds: int) -> float:
    return stake * odds / 100.0 if odds > 0 else stake * 100.0 / abs(odds)


def validate_closing_line(record: Mapping[str, Any]) -> None:
    _validate_identity(record, "closing_line_id")
    expected_fields = {
        "schema_version", "record_type", "classification", "prospective_evidence",
        "game_id", "kickoff_at", "closing_observation_id", "closing_collected_at",
        "minutes_before_kickoff", "provider", "books", "consensus_home_probability",
        "consensus_away_probability", "draftkings_home_break_even_probability",
        "draftkings_away_break_even_probability", "closing_line_id",
    }
    if set(record) != expected_fields:
        raise ClosingSettlementError("closing-line fields are invalid")
    if (
        record.get("schema_version") != 1
        or record.get("record_type") != "CLOSING_LINE_OBSERVATION"
        or record.get("classification") != CLOSE_CLASSIFICATION
        or record.get("prospective_evidence") is not False
    ):
        raise ClosingSettlementError("closing-line identity fields are invalid")
    kickoff = _timestamp(record.get("kickoff_at"), "kickoff_at")
    collected = _timestamp(record.get("closing_collected_at"), "closing_collected_at")
    minutes = _number(record.get("minutes_before_kickoff"), "minutes_before_kickoff")
    if collected >= kickoff or not math.isclose(minutes, (kickoff - collected).total_seconds() / 60.0, abs_tol=1e-12):
        raise ClosingSettlementError("closing-line timing is invalid")
    books = record.get("books")
    if not isinstance(books, Mapping) or set(books) != set(BOOKS):
        raise ClosingSettlementError("closing line requires exactly three books")
    fair_home = []
    for name in BOOKS:
        book = books[name]
        if not isinstance(book, Mapping) or set(book) != {"home_odds", "away_odds"}:
            raise ClosingSettlementError("closing book fields are invalid")
        fair = remove_two_sided_vig(
            _odds(book["home_odds"], f"{name} home odds"),
            _odds(book["away_odds"], f"{name} away odds"),
        )
        fair_home.append(fair.home_fair_probability)
    expected_home = sum(fair_home) / len(fair_home)
    dk = books["DraftKings"]
    expected = {
        "consensus_home_probability": expected_home,
        "consensus_away_probability": 1.0 - expected_home,
        "draftkings_home_break_even_probability": american_odds_to_implied_probability(dk["home_odds"]),
        "draftkings_away_break_even_probability": american_odds_to_implied_probability(dk["away_odds"]),
    }
    for field, value in expected.items():
        if not math.isclose(_number(record.get(field), field), value, abs_tol=1e-12):
            raise ClosingSettlementError(f"{field} is inconsistent")
    _game_id(record.get("game_id"))
    _text(record.get("provider"), "provider")
    _sha256(record.get("closing_observation_id"), "closing_observation_id")


def build_settlement(
    execution: Mapping[str, Any], final_result: Mapping[str, Any],
    *, closing_line: Mapping[str, Any] | None, settled_at: str,
) -> dict[str, Any]:
    execution = _mapping(execution, "execution")
    final_result = _mapping(final_result, "final_result")
    validate_execution(execution)
    validate_final_result(final_result)
    if execution["game_id"] != final_result["game_id"]:
        raise ClosingSettlementError("execution and final-result game identities differ")
    if _timestamp(final_result["acquired_at"], "final_result.acquired_at") < _timestamp(
        execution["kickoff_at"], "execution.kickoff_at"
    ):
        raise ClosingSettlementError("final result cannot be acquired before kickoff")
    home_score, away_score = final_result["home_score"], final_result["away_score"]
    winning_side = "PUSH" if home_score == away_score else ("HOME" if home_score > away_score else "AWAY")
    outcome = "PUSH" if winning_side == "PUSH" else ("WIN" if execution["side"] == winning_side else "LOSS")
    funding_type = execution.get("funding_type", "CASH")
    if funding_type == "BONUS_BET" and outcome == "PUSH":
        raise ClosingSettlementError(
            "BONUS_BET push requires explicit sportsbook reissue handling"
        )
    net_profit = (
        0.0
        if outcome == "PUSH"
        else (
            _profit(execution["stake"], execution["american_odds"])
            if outcome == "WIN"
            else (-execution["stake"] if funding_type == "CASH" else 0.0)
        )
    )
    execution_break_even = american_odds_to_implied_probability(execution["american_odds"])
    close_odds = close_break_even = close_consensus = None
    closing_id = None
    if closing_line is not None:
        closing_line = _mapping(closing_line, "closing_line")
        validate_closing_line(closing_line)
        if closing_line.get("game_id") != execution["game_id"]:
            raise ClosingSettlementError("execution and closing-line game identities differ")
        side_key = execution["side"].lower()
        close_odds = closing_line["books"]["DraftKings"][f"{side_key}_odds"]
        close_break_even = closing_line[f"draftkings_{side_key}_break_even_probability"]
        close_consensus = closing_line[f"consensus_{side_key}_probability"]
        closing_id = closing_line["closing_observation_id"]
    settled_text = _utc_text(settled_at, "settled_at")
    if _timestamp(settled_text, "settled_at") < _timestamp(final_result["acquired_at"], "final_result.acquired_at"):
        raise ClosingSettlementError("settlement cannot precede final-result acquisition")
    base = {
        "schema_version": 1 if execution["schema_version"] == 1 else 2,
        "record_type": "EXECUTION_SETTLEMENT",
        "classification": SETTLEMENT_CLASSIFICATION,
        "prospective_evidence": False,
        "execution": dict(execution),
        "final_result": dict(final_result),
        "closing_line": None if closing_line is None else dict(closing_line),
        "execution_id": execution["execution_id"],
        "game_id": execution["game_id"],
        "final_result_id": final_result["final_result_id"],
        "closing_observation_id": closing_id,
        "settled_at": settled_text,
        "outcome": outcome,
        "stake": execution["stake"],
        "currency": execution["currency"],
        "execution_odds": execution["american_odds"],
        "closing_draftkings_odds_same_side": close_odds,
        "net_profit": net_profit,
        "execution_break_even_probability": execution_break_even,
        "closing_draftkings_break_even_probability_same_side": close_break_even,
        "closing_consensus_probability_same_side": close_consensus,
        "draftkings_clv_probability": None if close_break_even is None else close_break_even - execution_break_even,
        "consensus_clv_probability": None if close_consensus is None else close_consensus - execution_break_even,
    }
    if execution["schema_version"] == 2:
        bonus_proceeds = net_profit if funding_type == "BONUS_BET" else None
        base.update(
            {
                "funding_type": funding_type,
                "cash_staked": execution["stake"] if funding_type == "CASH" else 0.0,
                "bonus_face_value_consumed": (
                    execution["stake"] if funding_type == "BONUS_BET" else 0.0
                ),
                "bonus_cash_proceeds": bonus_proceeds,
                "bonus_conversion_rate": (
                    bonus_proceeds / execution["stake"]
                    if funding_type == "BONUS_BET"
                    else None
                ),
                "realized_cash_change": net_profit,
            }
        )
    return {**base, "settlement_id": _identity(base)}


def _read(path: Path | str, identity_field: str, validator: Any) -> tuple[dict[str, Any], ...]:
    source = Path(path)
    if not source.exists():
        return ()
    rows = []
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ClosingSettlementError(f"blank line {number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ClosingSettlementError(f"invalid JSON at line {number}") from exc
        if not isinstance(row, dict):
            raise ClosingSettlementError(f"line {number} is not an object")
        validator(row)
        rows.append(row)
    identities = [row[identity_field] for row in rows]
    if len(identities) != len(set(identities)):
        raise ClosingSettlementError(f"duplicate {identity_field}")
    return tuple(rows)


def read_executions(path: Path | str) -> tuple[dict[str, Any], ...]:
    return _read(path, "execution_id", validate_execution)


def append_execution(path: Path | str, record: Mapping[str, Any]) -> None:
    validate_execution(record)
    existing = read_executions(path)
    if any(row["execution_id"] == record["execution_id"] for row in existing):
        raise ClosingSettlementError("duplicate execution")
    _append(path, record)


def validate_settlement(record: Mapping[str, Any]) -> None:
    _validate_identity(record, "settlement_id")
    expected = build_settlement(
        record.get("execution"), record.get("final_result"),
        closing_line=record.get("closing_line"), settled_at=record.get("settled_at"),
    )
    if dict(record) != expected:
        raise ClosingSettlementError("settlement fields or semantics are invalid")


def read_settlements(path: Path | str) -> tuple[dict[str, Any], ...]:
    rows = _read(path, "settlement_id", validate_settlement)
    execution_ids = [row["execution_id"] for row in rows]
    if len(execution_ids) != len(set(execution_ids)):
        raise ClosingSettlementError("contradictory settlement for execution")
    return rows


def append_settlement(path: Path | str, record: Mapping[str, Any]) -> None:
    validate_settlement(record)
    existing = read_settlements(path)
    if any(row["execution_id"] == record["execution_id"] for row in existing):
        raise ClosingSettlementError("execution is already settled")
    _append(path, record)


def _append(path: Path | str, record: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
