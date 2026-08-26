"""Offline deterministic market ingestion boundary for Step 91D."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from gridiron.market.prospective_ledger import (
    CANDIDATE_ID,
    CONSENSUS_BOOKS,
    EXECUTION_BOOK,
    PROTOCOL_ID,
    LedgerError,
    build_decision,
    capture_decision,
)

_TOP_LEVEL_KEYS = {
    "schema_version",
    "provider",
    "captured_at",
    "game",
    "def_epa",
    "offers",
}
_GAME_KEYS = {
    "game_id",
    "season",
    "season_type",
    "week",
    "kickoff_at",
    "home_team",
    "away_team",
}
_OFFER_KEYS = {
    "book",
    "market",
    "home_team",
    "away_team",
    "home_odds",
    "away_odds",
    "observed_at",
}
BOOK_ALIASES = {
    "Bet365": "Bet365",
    "bet365": "Bet365",
    "SI": "SI",
    "si": "SI",
    "Sports Illustrated": "SI",
    "Betway": "Betway",
    "betway": "Betway",
    "BetMGM": "BetMGM",
    "betmgm": "BetMGM",
    "Bet MGM": "BetMGM",
    "FanDuel": "FanDuel",
    "fanduel": "FanDuel",
    "Fan Duel": "FanDuel",
    "Caesars": "Caesars",
    "caesars": "Caesars",
    "Caesars Sportsbook": "Caesars",
    "DraftKings": "DraftKings",
    "draftkings": "DraftKings",
    "Draft Kings": "DraftKings",
}


class ProspectiveMarketIngestionError(ValueError):
    """Raised when a Step 91D snapshot cannot be ingested."""


def _reject_json_constant(value: str) -> None:
    raise ProspectiveMarketIngestionError(f"invalid JSON numeric constant: {value}")


def load_market_snapshot(path: Path | str) -> dict[str, Any]:
    """Load one strict JSON object from disk without accepting NaN or Infinity."""
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except OSError as exc:
        raise ProspectiveMarketIngestionError(
            f"cannot read market snapshot: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProspectiveMarketIngestionError(
            f"invalid market snapshot JSON: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise ProspectiveMarketIngestionError("market snapshot must be a JSON object")
    return value


def _exact_keys(value: object, expected: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProspectiveMarketIngestionError(f"{field} must be an object")
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown:
        raise ProspectiveMarketIngestionError(
            f"{field} contains unknown keys: {', '.join(unknown)}"
        )
    if missing:
        raise ProspectiveMarketIngestionError(
            f"{field} is missing keys: {', '.join(missing)}"
        )
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProspectiveMarketIngestionError(f"{field} must be an integer")
    return value


def _timestamp(value: object, field: str) -> tuple[datetime, str]:
    if not isinstance(value, str):
        raise ProspectiveMarketIngestionError(
            f"{field} must be an ISO-8601 timestamp"
        )
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ProspectiveMarketIngestionError(
            f"{field} must be an ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise ProspectiveMarketIngestionError(f"{field} must include a timezone")
    utc = parsed.astimezone(UTC)
    return utc, utc.isoformat().replace("+00:00", "Z")


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProspectiveMarketIngestionError(f"{field} must be a non-empty string")
    return value.strip()


def _american_odds(value: object, field: str) -> int:
    odds = _integer(value, field)
    if -100 < odds < 100:
        raise ProspectiveMarketIngestionError(
            f"{field} must be <= -100 or >= 100"
        )
    return odds


def _validate_contract() -> None:
    expected_books = (
        "Bet365",
        "SI",
        "Betway",
        "BetMGM",
        "FanDuel",
        "Caesars",
        "DraftKings",
    )
    if CONSENSUS_BOOKS != expected_books:
        raise ProspectiveMarketIngestionError(
            "Step 91C consensus-book contract does not match Step 91D"
        )
    if EXECUTION_BOOK != "DraftKings":
        raise ProspectiveMarketIngestionError(
            "Step 91C execution-book contract does not match Step 91D"
        )
    if PROTOCOL_ID != "step91b-prospective-validation-v1":
        raise ProspectiveMarketIngestionError(
            "Step 91C protocol identity does not match Step 91D"
        )
    if CANDIDATE_ID != "market-plus-def-epa-capped-0425-v1":
        raise ProspectiveMarketIngestionError(
            "Step 91C candidate identity does not match Step 91D"
        )


def normalize_market_snapshot(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Strictly validate and deterministically normalize one raw snapshot."""
    _validate_contract()
    top = _exact_keys(raw, _TOP_LEVEL_KEYS, "snapshot")
    if _integer(top["schema_version"], "schema_version") != 1:
        raise ProspectiveMarketIngestionError("schema_version must equal 1")
    provider = _nonempty_string(top["provider"], "provider")
    captured_dt, captured_at = _timestamp(top["captured_at"], "captured_at")

    game = _exact_keys(top["game"], _GAME_KEYS, "game")
    game_id = _nonempty_string(game["game_id"], "game.game_id")
    if _integer(game["season"], "game.season") != 2026:
        raise ProspectiveMarketIngestionError("game.season must equal 2026")
    if game["season_type"] != "REG":
        raise ProspectiveMarketIngestionError("game.season_type must equal REG")
    week = _integer(game["week"], "game.week")
    if not 1 <= week <= 16:
        raise ProspectiveMarketIngestionError("game.week must be from 1 through 16")
    kickoff_dt, kickoff_at = _timestamp(game["kickoff_at"], "game.kickoff_at")
    if captured_dt >= kickoff_dt:
        raise ProspectiveMarketIngestionError(
            "captured_at must be strictly earlier than game.kickoff_at"
        )
    home_team = _nonempty_string(game["home_team"], "game.home_team")
    away_team = _nonempty_string(game["away_team"], "game.away_team")
    if home_team == away_team:
        raise ProspectiveMarketIngestionError(
            "game.home_team and game.away_team must be different"
        )

    def_epa = top["def_epa"]
    if def_epa is None:
        if week != 1:
            raise ProspectiveMarketIngestionError(
                "def_epa may be null only in Week 1"
            )
    elif isinstance(def_epa, bool) or not isinstance(def_epa, (int, float)):
        raise ProspectiveMarketIngestionError("def_epa must be a finite JSON number")
    elif not math.isfinite(def_epa):
        raise ProspectiveMarketIngestionError("def_epa must be finite")

    offers = top["offers"]
    if not isinstance(offers, list) or not offers:
        raise ProspectiveMarketIngestionError("offers must be a non-empty list")
    by_book: dict[str, list[dict[str, Any]]] = {}
    for index, raw_offer in enumerate(offers):
        field = f"offers[{index}]"
        offer = _exact_keys(raw_offer, _OFFER_KEYS, field)
        raw_book = offer["book"]
        if not isinstance(raw_book, str) or raw_book not in BOOK_ALIASES:
            raise ProspectiveMarketIngestionError(
                f"{field}.book is not a recognized explicit alias: {raw_book!r}"
            )
        book = BOOK_ALIASES[raw_book]
        if offer["market"] != "moneyline":
            raise ProspectiveMarketIngestionError(f"{field}.market must equal moneyline")
        if offer["home_team"] != home_team or offer["away_team"] != away_team:
            raise ProspectiveMarketIngestionError(
                f"{field} teams must exactly match the game"
            )
        observed_dt, observed_at = _timestamp(
            offer["observed_at"], f"{field}.observed_at"
        )
        if observed_dt > captured_dt:
            raise ProspectiveMarketIngestionError(
                f"{field}.observed_at must not be later than captured_at"
            )
        normalized = {
            "book": book,
            "market": "moneyline",
            "home_team": home_team,
            "away_team": away_team,
            "home_odds": _american_odds(offer["home_odds"], f"{field}.home_odds"),
            "away_odds": _american_odds(offer["away_odds"], f"{field}.away_odds"),
            "observed_at": observed_at,
        }
        by_book.setdefault(book, []).append(normalized)

    missing = [book for book in CONSENSUS_BOOKS if book not in by_book]
    if missing:
        raise ProspectiveMarketIngestionError(
            f"missing canonical books: {', '.join(missing)}"
        )
    selected = []
    for book in CONSENSUS_BOOKS:
        observations = by_book[book]
        latest_dt = max(
            _timestamp(item["observed_at"], "observed_at")[0]
            for item in observations
        )
        latest = [
            item
            for item in observations
            if _timestamp(item["observed_at"], "observed_at")[0] == latest_dt
        ]
        latest_at = latest[0]["observed_at"]
        unique = {
            json.dumps(item, sort_keys=True, separators=(",", ":")) for item in latest
        }
        if len(unique) != 1:
            raise ProspectiveMarketIngestionError(
                f"ambiguous latest observation for {book} at {latest_at}"
            )
        selected.append(latest[0])

    return {
        "schema_version": 1,
        "provider": provider,
        "captured_at": captured_at,
        "game": {
            "game_id": game_id,
            "season": 2026,
            "season_type": "REG",
            "week": week,
            "kickoff_at": kickoff_at,
            "home_team": home_team,
            "away_team": away_team,
        },
        "def_epa": def_epa,
        "offers": selected,
    }


def build_ledger_payload(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Build the exact normalized payload consumed by Step 91C."""
    normalized = normalize_market_snapshot(raw)
    game = normalized["game"]
    observations = [
        {
            "book": offer["book"],
            "home_odds": offer["home_odds"],
            "away_odds": offer["away_odds"],
            "observed_at": offer["observed_at"],
        }
        for offer in normalized["offers"]
    ]
    draftkings = next(
        item for item in observations if item["book"] == EXECUTION_BOOK
    )
    return {
        "game_id": game["game_id"],
        "season": game["season"],
        "season_type": game["season_type"],
        "week": game["week"],
        "kickoff_at": game["kickoff_at"],
        "decision_at": normalized["captured_at"],
        "home_team": game["home_team"],
        "away_team": game["away_team"],
        "def_epa": normalized["def_epa"],
        "market_observations": observations,
        "execution_prices": {
            "book": EXECUTION_BOOK,
            "home_odds": draftkings["home_odds"],
            "away_odds": draftkings["away_odds"],
        },
    }


def preview_market_decision(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Return Step 91C's exact DECISION without touching a ledger."""
    try:
        return build_decision(build_ledger_payload(raw))
    except LedgerError as exc:
        raise ProspectiveMarketIngestionError(
            f"Step 91C rejected the normalized snapshot: {exc}"
        ) from exc


def capture_market_decision(
    ledger_path: Path | str, raw: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate fully, then ask Step 91C to append one DECISION."""
    payload = build_ledger_payload(raw)
    try:
        return capture_decision(ledger_path, payload)
    except LedgerError as exc:
        raise ProspectiveMarketIngestionError(
            f"Step 91C rejected the normalized snapshot: {exc}"
        ) from exc
