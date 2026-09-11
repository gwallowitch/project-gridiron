"""Append-only non-prospective history for operational market observations."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gridiron.market.model_math import calculate_market_model_decision
from gridiron.market.moneyline import (
    american_odds_to_implied_probability,
    remove_two_sided_vig,
)
from gridiron.market.prospective_ledger import (
    DEF_EPA_COEFFICIENT,
    INTERCEPT,
    MARKET_COEFFICIENT,
    RESIDUAL_CAP,
)

SCHEMA_VERSION = 2
RECORD_TYPE = "OPERATIONAL_MARKET_OBSERVATION"
CLASSIFICATION = "NON_PROSPECTIVE_OPERATIONAL_MARKET_HISTORY"
BOOKS = ("BetMGM", "FanDuel", "DraftKings")
OPERATIONAL_IDENTITY = "market-plus-def-epa-capped-0425-operational-three-book-v1"
TWO_SIDED_EXECUTION_IDENTITY = "two-sided-execution-observation-v1"
TWO_SIDED_EXECUTION_CLASSIFICATION = (
    "NON_PROSPECTIVE_TWO_SIDED_EXECUTION_OBSERVATION"
)
MAX_QUOTE_AGE_MINUTES = 10.0
BLOCKING_WARNING_MARKERS = (
    ":STALE_PRICE_",
    ":MISSING_PRICE",
    ":MISSING_TIMESTAMP",
    ":MISSING_BOOK",
    ":TIMESTAMP_AFTER_CAPTURE",
)


class OperationalHistoryError(ValueError):
    """An operational observation cannot be safely retained."""


class DuplicateOperationalObservationError(OperationalHistoryError):
    """The exact captured operational observation already exists."""


def canonical_json(value: object) -> str:
    """Serialize one record deterministically and reject non-finite numbers."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise OperationalHistoryError(
            "operational history contains non-canonical values"
        ) from exc


def _required(mapping: Mapping[str, Any], field: str) -> Any:
    value = mapping.get(field)
    if value is None:
        raise OperationalHistoryError(f"operational result is missing {field}")
    return value


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OperationalHistoryError(f"{field} must be an object")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OperationalHistoryError(f"{field} must be a non-empty string")
    return value


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OperationalHistoryError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise OperationalHistoryError(f"{field} must be finite")
    return result


def _probability(value: Any, field: str) -> float:
    result = _number(value, field)
    if not 0.0 <= result <= 1.0:
        raise OperationalHistoryError(f"{field} must be between 0 and 1")
    return result


def _timestamp(value: Any, field: str) -> datetime:
    text = _text(value, field)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        result = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise OperationalHistoryError(f"{field} must be ISO-8601") from exc
    if result.tzinfo is None:
        raise OperationalHistoryError(f"{field} must include a timezone")
    return result.astimezone(UTC)


def _same(actual: float, expected: float, field: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-15):
        raise OperationalHistoryError(f"{field} is inconsistent")


def _american_odds(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OperationalHistoryError(f"{field} must be integer American odds")
    if -100 < value < 100:
        raise OperationalHistoryError(f"{field} must be <= -100 or >= +100")
    american_odds_to_implied_probability(value)
    return value


def calculate_two_sided_execution_observation(
    *,
    model_home_probability: float,
    model_away_probability: float,
    draftkings_home_odds: int,
    draftkings_away_odds: int,
    frozen_selected_side: str,
    frozen_is_bet: bool,
) -> dict[str, Any]:
    """Derive a non-prospective challenger from one completed prediction."""
    model_home = _probability(model_home_probability, "model_home_probability")
    model_away = _probability(model_away_probability, "model_away_probability")
    _same(model_away, 1.0 - model_home, "model_away_probability")
    home_odds = _american_odds(draftkings_home_odds, "draftkings_home_odds")
    away_odds = _american_odds(draftkings_away_odds, "draftkings_away_odds")
    if frozen_selected_side not in {"HOME", "AWAY"}:
        raise OperationalHistoryError("frozen_selected_side must be HOME or AWAY")
    if not isinstance(frozen_is_bet, bool):
        raise OperationalHistoryError("frozen_is_bet must be boolean")

    home_break_even = american_odds_to_implied_probability(home_odds)
    away_break_even = american_odds_to_implied_probability(away_odds)
    home_edge = model_home - home_break_even
    away_edge = model_away - away_break_even
    home_positive = home_edge > 0.0
    away_positive = away_edge > 0.0
    if home_edge > away_edge:
        best_side = "HOME"
        best_edge = home_edge
    elif away_edge > home_edge:
        best_side = "AWAY"
        best_edge = away_edge
    else:
        best_side = "TIE"
        best_edge = home_edge

    opposite_side = "AWAY" if frozen_selected_side == "HOME" else "HOME"
    opposite_edge = away_edge if opposite_side == "AWAY" else home_edge
    opposite_positive = opposite_edge > 0.0
    return {
        "classification": TWO_SIDED_EXECUTION_CLASSIFICATION,
        "identity": TWO_SIDED_EXECUTION_IDENTITY,
        "draftkings": {
            "home_break_even_probability": home_break_even,
            "away_break_even_probability": away_break_even,
        },
        "home": {
            "model_probability": model_home,
            "edge": home_edge,
            "positive_edge": home_positive,
        },
        "away": {
            "model_probability": model_away,
            "edge": away_edge,
            "positive_edge": away_positive,
        },
        "best_side": best_side,
        "best_edge": best_edge,
        "both_sides_positive": home_positive and away_positive,
        "frozen_selected_side": frozen_selected_side,
        "frozen_is_bet": frozen_is_bet,
        "opposite_side": opposite_side,
        "opposite_side_edge": opposite_edge,
        "opposite_side_positive": opposite_positive,
        "missed_opposite_side_positive_edge": (
            not frozen_is_bet and opposite_positive
        ),
    }


def _validate_two_sided_execution(
    value: Any, expected: Mapping[str, Any]
) -> None:
    actual = _mapping(value, "two_sided_execution")
    if set(actual) != set(expected):
        raise OperationalHistoryError("two_sided_execution fields are invalid")
    for field in ("classification", "identity", "best_side", "opposite_side"):
        if actual.get(field) != expected[field]:
            raise OperationalHistoryError(f"two_sided_execution.{field} is inconsistent")
    for field in (
        "both_sides_positive",
        "frozen_is_bet",
        "opposite_side_positive",
        "missed_opposite_side_positive_edge",
    ):
        if not isinstance(actual.get(field), bool) or actual[field] is not expected[field]:
            raise OperationalHistoryError(f"two_sided_execution.{field} is inconsistent")
    for field in ("best_edge", "opposite_side_edge"):
        number = _number(_required(actual, field), f"two_sided_execution.{field}")
        _same(number, expected[field], f"two_sided_execution.{field}")
    for section in ("draftkings", "home", "away"):
        actual_section = _mapping(_required(actual, section), f"two_sided_execution.{section}")
        expected_section = expected[section]
        if set(actual_section) != set(expected_section):
            raise OperationalHistoryError(
                f"two_sided_execution.{section} fields are invalid"
            )
        for field, expected_value in expected_section.items():
            actual_value = _required(
                actual_section, field
            )
            qualified = f"two_sided_execution.{section}.{field}"
            if isinstance(expected_value, bool):
                if not isinstance(actual_value, bool) or actual_value is not expected_value:
                    raise OperationalHistoryError(f"{qualified} is inconsistent")
            else:
                _same(_number(actual_value, qualified), expected_value, qualified)
    if actual.get("frozen_selected_side") != expected["frozen_selected_side"]:
        raise OperationalHistoryError(
            "two_sided_execution.frozen_selected_side is inconsistent"
        )


def _validate_record_semantics(record: Mapping[str, Any]) -> None:
    if record.get("schema_version") != SCHEMA_VERSION:
        raise OperationalHistoryError("unsupported operational history schema_version")
    if record.get("record_type") != RECORD_TYPE:
        raise OperationalHistoryError("invalid operational history record_type")
    if record.get("classification") != CLASSIFICATION:
        raise OperationalHistoryError("invalid operational history classification")
    if record.get("prospective_evidence") is not False:
        raise OperationalHistoryError("prospective_evidence must be exactly false")

    game = _mapping(_required(record, "game"), "game")
    game_id = _text(_required(game, "game_id"), "game.game_id")
    season = _required(game, "season")
    week = _required(game, "week")
    if isinstance(season, bool) or not isinstance(season, int) or season != 2026:
        raise OperationalHistoryError("game.season must be 2026")
    if isinstance(week, bool) or not isinstance(week, int) or not 1 <= week <= 16:
        raise OperationalHistoryError("game.week must be an integer from 1 through 16")
    if game.get("season_type") != "REG":
        raise OperationalHistoryError("game.season_type must be REG")
    home_team = _text(_required(game, "home_team"), "game.home_team")
    away_team = _text(_required(game, "away_team"), "game.away_team")
    if home_team == away_team:
        raise OperationalHistoryError("home and away teams must be distinct")
    if game_id != f"{season}_{week:02d}_{away_team}_{home_team}":
        raise OperationalHistoryError("game.game_id is not canonical")
    kickoff = _timestamp(_required(game, "kickoff_at"), "game.kickoff_at")

    timing = _mapping(_required(record, "timing"), "timing")
    collected = _timestamp(_required(timing, "collected_at"), "timing.collected_at")
    predicted = _timestamp(
        _required(timing, "prediction_at"), "timing.prediction_at"
    )
    if collected != predicted:
        raise OperationalHistoryError("collection and prediction timestamps must match")
    if collected >= kickoff:
        raise OperationalHistoryError("operational observation must be pre-kickoff")
    minutes = _number(
        _required(timing, "minutes_to_kickoff"), "timing.minutes_to_kickoff"
    )
    hours = _number(
        _required(timing, "hours_to_kickoff"), "timing.hours_to_kickoff"
    )
    expected_minutes = (kickoff - collected).total_seconds() / 60.0
    if minutes <= 0.0:
        raise OperationalHistoryError("minutes_to_kickoff must be positive")
    _same(minutes, expected_minutes, "timing.minutes_to_kickoff")
    _same(hours, minutes / 60.0, "timing.hours_to_kickoff")
    _text(_required(record, "provider"), "provider")

    raw_books = record.get("books")
    if not isinstance(raw_books, list):
        raise OperationalHistoryError("books must be an array")
    if len(raw_books) != len(BOOKS):
        raise OperationalHistoryError("exactly three operational books are required")
    by_book: dict[str, Mapping[str, Any]] = {}
    fair_home: list[float] = []
    for index, raw_book in enumerate(raw_books):
        book = _mapping(raw_book, f"books[{index}]")
        name = _text(_required(book, "book"), f"books[{index}].book")
        if name not in BOOKS:
            raise OperationalHistoryError(f"unexpected operational book: {name}")
        if name in by_book:
            raise OperationalHistoryError(f"duplicate operational book: {name}")
        by_book[name] = book
        home_odds = _american_odds(
            _required(book, "home_odds"), f"{name}.home_odds"
        )
        away_odds = _american_odds(
            _required(book, "away_odds"), f"{name}.away_odds"
        )
        observed = _timestamp(_required(book, "observed_at"), f"{name}.observed_at")
        age = (collected - observed).total_seconds() / 60.0
        if age < 0.0 or age > MAX_QUOTE_AGE_MINUTES:
            raise OperationalHistoryError(f"{name} observation timestamp is invalid")
        fair = remove_two_sided_vig(home_odds, away_odds)
        stored_home = _probability(
            _required(book, "home_no_vig_probability"),
            f"{name}.home_no_vig_probability",
        )
        stored_away = _probability(
            _required(book, "away_no_vig_probability"),
            f"{name}.away_no_vig_probability",
        )
        _same(stored_home, fair.home_fair_probability, f"{name} home no-vig")
        _same(stored_away, fair.away_fair_probability, f"{name} away no-vig")
        fair_home.append(stored_home)
    if set(by_book) != set(BOOKS):
        raise OperationalHistoryError("required operational book identities are missing")

    market = _mapping(_required(record, "market"), "market")
    if market.get("consensus") != "equal-mean-three-book-no-vig":
        raise OperationalHistoryError("invalid operational consensus identity")
    market_home = _probability(
        _required(market, "home_probability"), "market.home_probability"
    )
    market_away = _probability(
        _required(market, "away_probability"), "market.away_probability"
    )
    _same(market_home, sum(fair_home) / len(BOOKS), "market.home_probability")
    _same(market_away, 1.0 - market_home, "market.away_probability")

    def_epa = _mapping(_required(record, "def_epa"), "def_epa")
    if def_epa.get("feature") != "def_epa_trend_advantage":
        raise OperationalHistoryError("invalid DEF EPA feature identity")
    def_epa_value = _number(_required(def_epa, "value"), "def_epa.value")
    def_epa_source = _text(_required(def_epa, "source"), "def_epa.source")
    if week == 1 and (
        def_epa_value != 0.0 or def_epa_source != "frozen Week 1 neutral rule"
    ):
        raise OperationalHistoryError(
            "Week 1 DEF EPA must use the frozen neutral rule"
        )

    model = _mapping(_required(record, "model"), "model")
    if model.get("operational_identity") != OPERATIONAL_IDENTITY:
        raise OperationalHistoryError("invalid operational model identity")
    coefficients = _mapping(_required(model, "coefficients"), "model.coefficients")
    expected_coefficients = {
        "market": MARKET_COEFFICIENT,
        "def_epa": DEF_EPA_COEFFICIENT,
        "intercept": INTERCEPT,
        "residual_cap": RESIDUAL_CAP,
    }
    if dict(coefficients) != expected_coefficients:
        raise OperationalHistoryError("invalid frozen model coefficients")

    draftkings = by_book["DraftKings"]
    decision = calculate_market_model_decision(
        market_home,
        def_epa_value,
        home_odds=draftkings["home_odds"],
        away_odds=draftkings["away_odds"],
        market_coefficient=MARKET_COEFFICIENT,
        def_epa_coefficient=DEF_EPA_COEFFICIENT,
        intercept=INTERCEPT,
        residual_cap=RESIDUAL_CAP,
    )
    model_home = _probability(
        _required(model, "home_probability"), "model.home_probability"
    )
    model_away = _probability(
        _required(model, "away_probability"), "model.away_probability"
    )
    _same(model_home, decision.model_home_probability, "model.home_probability")
    _same(model_away, 1.0 - model_home, "model.away_probability")

    stored_decision = _mapping(_required(record, "decision"), "decision")
    if stored_decision.get("execution_book") != "DraftKings":
        raise OperationalHistoryError("execution_book must be DraftKings")
    if stored_decision.get("selected_side") != decision.selected_side:
        raise OperationalHistoryError("selected_side is inconsistent")
    if stored_decision.get("execution_odds") != decision.selected_odds:
        raise OperationalHistoryError("execution_odds is inconsistent")
    break_even = _probability(
        _required(stored_decision, "break_even_probability"),
        "decision.break_even_probability",
    )
    edge = _number(_required(stored_decision, "edge"), "decision.edge")
    _same(break_even, decision.break_even_probability, "break_even_probability")
    _same(edge, decision.edge, "decision.edge")
    is_bet = stored_decision.get("is_bet")
    if not isinstance(is_bet, bool) or is_bet is not (edge > 0.0):
        raise OperationalHistoryError("is_bet must equal strict edge > 0")
    if stored_decision.get("decision") != ("BET" if is_bet else "NO BET"):
        raise OperationalHistoryError("decision label is inconsistent with is_bet")

    expected_two_sided = calculate_two_sided_execution_observation(
        model_home_probability=model_home,
        model_away_probability=model_away,
        draftkings_home_odds=draftkings["home_odds"],
        draftkings_away_odds=draftkings["away_odds"],
        frozen_selected_side=decision.selected_side,
        frozen_is_bet=is_bet,
    )
    _validate_two_sided_execution(
        _required(record, "two_sided_execution"), expected_two_sided
    )

    warnings = record.get("warnings")
    if not isinstance(warnings, list) or not all(
        isinstance(warning, str) for warning in warnings
    ):
        raise OperationalHistoryError("warnings must be an array of strings")
    if any(marker in warning for warning in warnings for marker in BLOCKING_WARNING_MARKERS):
        raise OperationalHistoryError("blocking market warning cannot be persisted")


def build_operational_history_record(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one deterministic record from an already validated prediction."""
    prices = _required(result, "prices")
    probabilities = _required(result, "book_probabilities")
    if not isinstance(prices, Mapping) or not isinstance(probabilities, Mapping):
        raise OperationalHistoryError("operational book fields must be mappings")

    books = []
    for book in BOOKS:
        offer = prices.get(book)
        fair = probabilities.get(book)
        if not isinstance(offer, Mapping) or not isinstance(fair, Mapping):
            raise OperationalHistoryError(f"operational result is missing {book}")
        books.append(
            {
                "book": book,
                "home_odds": _required(offer, "home_odds"),
                "away_odds": _required(offer, "away_odds"),
                "observed_at": _required(offer, "observed_at"),
                "home_no_vig_probability": _required(fair, "home"),
                "away_no_vig_probability": _required(fair, "away"),
            }
        )

    minutes = float(_required(result, "minutes_to_kickoff"))
    if not math.isfinite(minutes) or minutes <= 0.0:
        raise OperationalHistoryError("observation must be strictly pre-kickoff")

    draftkings = next(book for book in books if book["book"] == "DraftKings")
    two_sided_execution = calculate_two_sided_execution_observation(
        model_home_probability=_required(result, "model_home_probability"),
        model_away_probability=_required(result, "model_away_probability"),
        draftkings_home_odds=draftkings["home_odds"],
        draftkings_away_odds=draftkings["away_odds"],
        frozen_selected_side=_required(result, "selected_side"),
        frozen_is_bet=_required(result, "is_bet"),
    )

    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": RECORD_TYPE,
        "classification": CLASSIFICATION,
        "prospective_evidence": False,
        "game": {
            "game_id": _required(result, "game_id"),
            "season": _required(result, "season"),
            "week": _required(result, "week"),
            "season_type": _required(result, "season_type"),
            "home_team": _required(result, "home_team"),
            "away_team": _required(result, "away_team"),
            "kickoff_at": _required(result, "kickoff_at"),
        },
        "timing": {
            "collected_at": _required(result, "captured_at"),
            "prediction_at": _required(result, "captured_at"),
            "minutes_to_kickoff": minutes,
            "hours_to_kickoff": minutes / 60.0,
        },
        "provider": _required(result, "provider"),
        "books": books,
        "market": {
            "consensus": "equal-mean-three-book-no-vig",
            "home_probability": _required(result, "market_home_probability"),
            "away_probability": _required(result, "market_away_probability"),
        },
        "def_epa": {
            "feature": "def_epa_trend_advantage",
            "value": _required(result, "def_epa"),
            "source": _required(result, "def_epa_source"),
        },
        "model": {
            "operational_identity": _required(result, "operational_identity"),
            "coefficients": _required(result, "coefficients"),
            "home_probability": _required(result, "model_home_probability"),
            "away_probability": _required(result, "model_away_probability"),
        },
        "decision": {
            "selected_side": _required(result, "selected_side"),
            "execution_book": "DraftKings",
            "execution_odds": _required(result, "selected_odds"),
            "break_even_probability": _required(
                result, "break_even_probability"
            ),
            "edge": _required(result, "edge"),
            "is_bet": _required(result, "is_bet"),
            "decision": "BET" if result["is_bet"] else "NO BET",
        },
        "two_sided_execution": two_sided_execution,
        "warnings": list(result.get("warnings", ())),
    }
    _validate_record_semantics(base)
    material = canonical_json(base).encode("utf-8")
    return {**base, "observation_id": hashlib.sha256(material).hexdigest()}


def read_operational_history(path: Path | str) -> tuple[dict[str, Any], ...]:
    """Read and validate a complete operational history without mutation."""
    history_path = Path(path)
    if not history_path.exists():
        return ()
    records = []
    identities: set[str] = set()
    for number, line in enumerate(
        history_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            raise OperationalHistoryError(f"blank history line {number}")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise OperationalHistoryError(
                f"invalid history JSON at line {number}"
            ) from exc
        if not isinstance(record, dict):
            raise OperationalHistoryError(f"history line {number} is not an object")
        identity = record.get("observation_id")
        material = dict(record)
        material.pop("observation_id", None)
        expected = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
        if identity != expected:
            raise OperationalHistoryError(f"invalid observation identity at line {number}")
        _validate_record_semantics(record)
        if identity in identities:
            raise OperationalHistoryError(f"duplicate observation at line {number}")
        identities.add(identity)
        records.append(record)
    return tuple(records)


def append_operational_observation(
    path: Path | str, result: Mapping[str, Any]
) -> dict[str, Any]:
    """Append one valid observation, rejecting an exact retry before writing."""
    record = build_operational_history_record(result)
    existing = read_operational_history(path)
    if any(item["observation_id"] == record["observation_id"] for item in existing):
        raise DuplicateOperationalObservationError(
            "exact operational observation is already recorded"
        )
    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(record) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return record
