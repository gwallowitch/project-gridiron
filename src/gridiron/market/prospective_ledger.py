"""Deterministic append-only ledger for Step 91C prospective validation."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CANDIDATE_ID = "market-plus-def-epa-capped-0425-v1"
PROTOCOL_ID = "step91b-prospective-validation-v1"
MARKET_COEFFICIENT = 4.980172
DEF_EPA_COEFFICIENT = 1.044827
INTERCEPT = -2.514766
RESIDUAL_CAP = 0.0425
CONSENSUS_BOOKS = (
    "Bet365",
    "SI",
    "Betway",
    "BetMGM",
    "FanDuel",
    "Caesars",
    "DraftKings",
)
EXECUTION_BOOK = "DraftKings"


class LedgerError(ValueError):
    """Raised when a prospective ledger invariant is violated."""


@dataclass(frozen=True, slots=True)
class LedgerState:
    """Validated decisions and settlements from a ledger."""

    decisions: dict[str, dict[str, Any]]
    settlements: dict[str, dict[str, Any]]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _identity(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _utc_datetime(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise LedgerError(f"{field} must be an ISO-8601 timestamp")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise LedgerError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise LedgerError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _utc_text(value: object, field: str) -> str:
    return _utc_datetime(value, field).isoformat().replace("+00:00", "Z")


def implied_probability(american_odds: int) -> float:
    """Return break-even probability for positive or negative American odds."""
    if isinstance(american_odds, bool) or not isinstance(american_odds, int):
        raise LedgerError("American odds must be an integer")
    if american_odds == 0 or -100 < american_odds < 100:
        raise LedgerError("American odds must be <= -100 or >= 100")
    if american_odds > 0:
        return 100.0 / (american_odds + 100.0)
    return -american_odds / (-american_odds + 100.0)


def unit_profit(american_odds: int) -> float:
    """Return profit on a one-unit winning stake."""
    if american_odds > 0:
        implied_probability(american_odds)
        return american_odds / 100.0
    implied_probability(american_odds)
    return 100.0 / -american_odds


def _book_observations(raw: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, list):
        raise LedgerError("market_observations must be a list")
    by_book: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("book"), str):
            raise LedgerError("each market observation requires a book")
        book = item["book"]
        if book in by_book:
            raise LedgerError(f"duplicate market observation for {book}")
        if book not in CONSENSUS_BOOKS:
            raise LedgerError(f"unexpected consensus book: {book}")
        home_odds = item.get("home_odds")
        away_odds = item.get("away_odds")
        if home_odds is None or away_odds is None:
            raise LedgerError(f"incomplete consensus odds for {book}")
        implied_probability(home_odds)
        implied_probability(away_odds)
        observed_at = _utc_text(item.get("observed_at"), "observed_at")
        by_book[book] = {
            "book": book,
            "home_odds": home_odds,
            "away_odds": away_odds,
            "observed_at": observed_at,
        }
    if set(by_book) != set(CONSENSUS_BOOKS):
        missing = sorted(set(CONSENSUS_BOOKS) - set(by_book))
        raise LedgerError(f"seven complete market observations required; missing {missing}")
    return tuple(by_book[book] for book in CONSENSUS_BOOKS)


def _consensus_home_probability(observations: Iterable[Mapping[str, Any]]) -> float:
    probabilities = []
    for item in observations:
        home_odds = item["home_odds"]
        away_odds = item["away_odds"]
        if home_odds is None or away_odds is None:
            raise LedgerError("consensus observation is incomplete")
        home = implied_probability(home_odds)
        away = implied_probability(away_odds)
        probabilities.append(home / (home + away))
    if len(probabilities) != len(CONSENSUS_BOOKS):
        raise LedgerError("seven complete market observations required")
    return sum(probabilities) / len(probabilities)


def _execution_prices(
    raw: object, observations: tuple[dict[str, Any], ...]
) -> dict[str, Any]:
    draftkings = next(item for item in observations if item["book"] == EXECUTION_BOOK)
    if raw is None:
        return {
            "book": EXECUTION_BOOK,
            "home_odds": draftkings["home_odds"],
            "away_odds": draftkings["away_odds"],
        }
    if not isinstance(raw, dict) or raw.get("book") != EXECUTION_BOOK:
        raise LedgerError("execution_prices must identify DraftKings")
    result = {"book": EXECUTION_BOOK}
    for side in ("home_odds", "away_odds"):
        odds = raw.get(side)
        if odds is not None:
            implied_probability(odds)
        result[side] = odds
    return result


def build_decision(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate raw inputs and build one deterministic DECISION event."""
    if payload.get("season") != 2026 or payload.get("season_type") != "REG":
        raise LedgerError("Step 91C accepts only the 2026 regular season")
    week = payload.get("week")
    if isinstance(week, bool) or not isinstance(week, int) or not 1 <= week <= 16:
        raise LedgerError("week must be in the frozen Weeks 1-16 window")
    game_id = payload.get("game_id")
    if not isinstance(game_id, str) or not game_id.strip():
        raise LedgerError("game_id is required")
    decision_at = _utc_text(payload.get("decision_at"), "decision_at")
    kickoff_at = _utc_text(payload.get("kickoff_at"), "kickoff_at")
    if _utc_datetime(decision_at, "decision_at") >= _utc_datetime(
        kickoff_at, "kickoff_at"
    ):
        raise LedgerError("decision timestamp must be pre-kickoff")
    observations = _book_observations(payload.get("market_observations"))
    if any(
        _utc_datetime(item["observed_at"], "observed_at")
        > _utc_datetime(decision_at, "decision_at")
        for item in observations
    ):
        raise LedgerError("market observations cannot postdate the decision")
    def_epa = payload.get("def_epa")
    if def_epa is None:
        if week == 1:
            def_epa = 0.0
        else:
            raise LedgerError("missing later-week DEF EPA is not allowed")
    if isinstance(def_epa, bool) or not isinstance(def_epa, (int, float)):
        raise LedgerError("def_epa must be numeric")
    def_epa = float(def_epa)
    if not math.isfinite(def_epa):
        raise LedgerError("def_epa must be finite")

    market_home = _consensus_home_probability(observations)
    raw_home = 1.0 / (
        1.0
        + math.exp(
            -(
                INTERCEPT
                + MARKET_COEFFICIENT * market_home
                + DEF_EPA_COEFFICIENT * def_epa
            )
        )
    )
    candidate_home = min(
        market_home + RESIDUAL_CAP,
        max(market_home - RESIDUAL_CAP, raw_home),
    )
    side = "HOME" if candidate_home >= market_home else "AWAY"
    candidate_probability = candidate_home if side == "HOME" else 1.0 - candidate_home
    execution = _execution_prices(payload.get("execution_prices"), observations)
    selected_odds = execution["home_odds"] if side == "HOME" else execution["away_odds"]
    break_even = None if selected_odds is None else implied_probability(selected_odds)
    edge = None if break_even is None else candidate_probability - break_even
    is_bet = edge is not None and edge > 0.0

    observation_material = {
        "protocol_id": PROTOCOL_ID,
        "game_id": game_id,
        "decision_at": decision_at,
        "market_observations": observations,
        "def_epa": def_epa,
    }
    event = {
        "event_type": "DECISION",
        "protocol_id": PROTOCOL_ID,
        "candidate_id": CANDIDATE_ID,
        "game_id": game_id,
        "season": 2026,
        "season_type": "REG",
        "week": week,
        "kickoff_at": kickoff_at,
        "decision_at": decision_at,
        "home_team": payload.get("home_team"),
        "away_team": payload.get("away_team"),
        "market_observations": list(observations),
        "execution_prices": execution,
        "def_epa": def_epa,
        "market_home_probability": market_home,
        "candidate_home_probability": candidate_home,
        "selected_side": side,
        "selected_execution_odds": selected_odds,
        "break_even_probability": break_even,
        "edge": edge,
        "is_bet": is_bet,
        "observation_id": _identity(observation_material),
    }
    event["event_id"] = _identity(event)
    return event


def build_settlement(
    decision: Mapping[str, Any], *, result: str, settled_at: object
) -> dict[str, Any]:
    """Build a SETTLEMENT using only captured decision-time odds."""
    if result not in {"HOME", "AWAY", "PUSH", "CANCELLED"}:
        raise LedgerError("result must be HOME, AWAY, PUSH, or CANCELLED")
    settled_text = _utc_text(settled_at, "settled_at")
    if _utc_datetime(settled_text, "settled_at") < _utc_datetime(
        decision["kickoff_at"], "kickoff_at"
    ):
        raise LedgerError("settlement cannot precede kickoff")
    profit = 0.0
    if decision["is_bet"] and result not in {"PUSH", "CANCELLED"}:
        if result == decision["selected_side"]:
            profit = unit_profit(decision["selected_execution_odds"])
        else:
            profit = -1.0
    event = {
        "event_type": "SETTLEMENT",
        "protocol_id": PROTOCOL_ID,
        "candidate_id": CANDIDATE_ID,
        "game_id": decision["game_id"],
        "decision_event_id": decision["event_id"],
        "settled_at": settled_text,
        "result": result,
        "captured_execution_odds": decision["selected_execution_odds"],
        "profit_units": profit,
    }
    event["event_id"] = _identity(event)
    return event


def _validate_decision(event: Mapping[str, Any]) -> dict[str, Any]:
    rebuilt = build_decision(event)
    if rebuilt != event:
        raise LedgerError(f"inconsistent DECISION event for {event.get('game_id')}")
    return rebuilt


def validate_events(events: Iterable[Mapping[str, Any]]) -> LedgerState:
    """Replay events and enforce all append-only ledger invariants."""
    decisions: dict[str, dict[str, Any]] = {}
    settlements: dict[str, dict[str, Any]] = {}
    event_ids: set[str] = set()
    for raw_event in events:
        event = dict(raw_event)
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or event_id in event_ids:
            raise LedgerError("missing or duplicate event identity")
        event_ids.add(event_id)
        game_id = event.get("game_id")
        if event.get("event_type") == "DECISION":
            if game_id in decisions:
                raise LedgerError(f"duplicate decision for {game_id}")
            decisions[game_id] = _validate_decision(event)
        elif event.get("event_type") == "SETTLEMENT":
            if game_id not in decisions:
                raise LedgerError(f"orphan settlement for {game_id}")
            if game_id in settlements:
                raise LedgerError(f"duplicate settlement for {game_id}")
            expected = build_settlement(
                decisions[game_id],
                result=event.get("result"),
                settled_at=event.get("settled_at"),
            )
            if expected != event:
                raise LedgerError(f"inconsistent settlement for {game_id}")
            settlements[game_id] = expected
        else:
            raise LedgerError("event_type must be DECISION or SETTLEMENT")
    return LedgerState(decisions=decisions, settlements=settlements)


def read_ledger(path: Path | str) -> tuple[dict[str, Any], ...]:
    """Read JSON Lines events without changing the ledger."""
    ledger_path = Path(path)
    if not ledger_path.exists():
        return ()
    events = []
    for line_number, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise LedgerError(f"blank ledger line at {line_number}")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LedgerError(f"invalid JSON on ledger line {line_number}") from exc
        if not isinstance(event, dict):
            raise LedgerError(f"ledger line {line_number} is not an object")
        events.append(event)
    return tuple(events)


def validate_ledger(path: Path | str) -> LedgerState:
    """Read and validate an entire ledger."""
    return validate_events(read_ledger(path))


def append_event(path: Path | str, event: Mapping[str, Any]) -> None:
    """Validate then durably append exactly one canonical JSON event."""
    ledger_path = Path(path)
    existing = read_ledger(ledger_path)
    validate_events((*existing, dict(event)))
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(_canonical_json(event) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def capture_decision(path: Path | str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build, validate, and append a DECISION event."""
    event = build_decision(payload)
    append_event(path, event)
    return event


def settle_decision(
    path: Path | str, *, game_id: str, result: str, settled_at: object
) -> dict[str, Any]:
    """Build, validate, and append a SETTLEMENT event."""
    state = validate_ledger(path)
    if game_id not in state.decisions:
        raise LedgerError(f"orphan settlement for {game_id}")
    if game_id in state.settlements:
        raise LedgerError(f"duplicate settlement for {game_id}")
    event = build_settlement(
        state.decisions[game_id], result=result, settled_at=settled_at
    )
    append_event(path, event)
    return event


def ledger_summary(path: Path | str) -> dict[str, Any]:
    """Return deterministic counts and settled economics."""
    state = validate_ledger(path)
    bets = [event for event in state.decisions.values() if event["is_bet"]]
    settled_bets = [
        state.settlements[game_id]
        for game_id in sorted(state.settlements)
        if state.decisions[game_id]["is_bet"]
    ]
    return {
        "decisions": len(state.decisions),
        "bets": len(bets),
        "non_bets": len(state.decisions) - len(bets),
        "settlements": len(state.settlements),
        "settled_bets": len(settled_bets),
        "unsettled_bets": len(bets) - len(settled_bets),
        "profit_units": sum(item["profit_units"] for item in settled_bets),
    }
