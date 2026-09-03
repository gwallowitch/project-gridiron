"""Render three sportsbook prices without producing a model decision."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BOOKS = ("BetMGM", "FanDuel", "DraftKings")
STALE_AFTER_MINUTES = 10.0


class ExploratoryPriceError(ValueError):
    """An exploratory price snapshot cannot be displayed safely."""


def _timestamp(value: object, field: str) -> tuple[datetime, str]:
    if not isinstance(value, str):
        raise ExploratoryPriceError(f"{field} must be an ISO-8601 timestamp")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ExploratoryPriceError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ExploratoryPriceError(f"{field} must include a timezone")
    utc = parsed.astimezone(UTC)
    return utc, utc.isoformat().replace("+00:00", "Z")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExploratoryPriceError(f"{field} must be a non-empty string")
    return value.strip()


def _odds(value: object, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExploratoryPriceError(f"{field} must be an integer or null")
    if -100 < value < 100:
        raise ExploratoryPriceError(f"{field} must be <= -100 or >= 100")
    return value


def load_exploratory_snapshot(path: Path | str) -> dict[str, Any]:
    """Load strict JSON without calling prospective ingestion or model code."""
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=lambda item: (_ for _ in ()).throw(
                ExploratoryPriceError(f"invalid JSON numeric constant: {item}")
            ),
        )
    except OSError as exc:
        raise ExploratoryPriceError(f"cannot read snapshot: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ExploratoryPriceError(f"invalid snapshot JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ExploratoryPriceError("snapshot must be a JSON object")
    return value


def _view_type(minutes_to_kickoff: float) -> tuple[str, list[str]]:
    if minutes_to_kickoff < 0:
        return "POST-KICKOFF", ["CAPTURE_OCCURRED_AFTER_KICKOFF"]
    if 55.0 <= minutes_to_kickoff <= 65.0:
        return "FINAL / NEAR-KICKOFF", []
    if minutes_to_kickoff >= 180.0:
        return "EARLY PREGAME", []
    return "OTHER PREGAME", ["OUTSIDE_EARLY_AND_NEAR_KICKOFF_WINDOWS"]


def build_exploratory_price_view(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Validate display fields and build a price-only, non-evidence view."""
    game = snapshot.get("game")
    offers = snapshot.get("offers")
    if not isinstance(game, dict):
        raise ExploratoryPriceError("game must be an object")
    if not isinstance(offers, list):
        raise ExploratoryPriceError("offers must be an array")
    captured, captured_text = _timestamp(snapshot.get("captured_at"), "captured_at")
    kickoff, kickoff_text = _timestamp(game.get("kickoff_at"), "game.kickoff_at")
    home = _text(game.get("home_team"), "game.home_team")
    away = _text(game.get("away_team"), "game.away_team")
    game_id = _text(game.get("game_id"), "game.game_id")
    minutes = (kickoff - captured).total_seconds() / 60.0
    view_type, warnings = _view_type(minutes)
    by_book: dict[str, dict[str, object]] = {}
    for index, raw in enumerate(offers):
        if not isinstance(raw, dict):
            raise ExploratoryPriceError(f"offers[{index}] must be an object")
        book = _text(raw.get("book"), f"offers[{index}].book")
        if book not in BOOKS:
            raise ExploratoryPriceError(f"unsupported exploratory book: {book}")
        if book in by_book:
            raise ExploratoryPriceError(f"duplicate exploratory book: {book}")
        observed_value = raw.get("observed_at")
        observed = observed_text = None
        if observed_value is not None:
            observed, observed_text = _timestamp(
                observed_value, f"offers[{index}].observed_at"
            )
        home_odds = _odds(raw.get("home_odds"), f"offers[{index}].home_odds")
        away_odds = _odds(raw.get("away_odds"), f"offers[{index}].away_odds")
        by_book[book] = {
            "home_odds": home_odds,
            "away_odds": away_odds,
            "observed_at": observed_text,
        }
        if home_odds is None or away_odds is None:
            warnings.append(f"{book}:MISSING_PRICE")
        if observed is None:
            warnings.append(f"{book}:MISSING_TIMESTAMP")
        else:
            age = (captured - observed).total_seconds() / 60.0
            if age < 0:
                warnings.append(f"{book}:TIMESTAMP_AFTER_CAPTURE")
            elif age > STALE_AFTER_MINUTES:
                warnings.append(f"{book}:STALE_PRICE_{age:.1f}_MINUTES")
    for book in BOOKS:
        if book not in by_book:
            warnings.append(f"{book}:MISSING_BOOK")
            by_book[book] = {
                "home_odds": None,
                "away_odds": None,
                "observed_at": None,
            }
    return {
        "game_id": game_id,
        "home_team": home,
        "away_team": away,
        "kickoff_at": kickoff_text,
        "captured_at": captured_text,
        "minutes_to_kickoff": minutes,
        "view_type": view_type,
        "prices": by_book,
        "warnings": tuple(warnings),
    }


def _price(value: object) -> str:
    return "N/A" if value is None else f"{int(value):+d}"


def format_exploratory_price_view(view: dict[str, Any]) -> str:
    """Render a concise PowerShell-friendly price-only report."""
    lines = [
        "GRIDIRON THREE-BOOK EXPLORATORY PRICE VIEWER",
        "NON-PROSPECTIVE — EXPLORATORY PRICES ONLY",
        "MODEL OUTPUTS: DISABLED",
        "",
        f"Game: {view['away_team']} @ {view['home_team']}",
        f"Game ID: {view['game_id']}",
        f"Kickoff: {view['kickoff_at']}",
        f"Captured: {view['captured_at']}",
        f"Minutes to kickoff: {view['minutes_to_kickoff']:.1f}",
        f"View: {view['view_type']}",
        "",
        "Prices (home / away):",
    ]
    for book in BOOKS:
        offer = view["prices"][book]
        lines.append(
            f"  {book}: {_price(offer['home_odds'])} / "
            f"{_price(offer['away_odds'])}  [{offer['observed_at'] or 'N/A'}]"
        )
    lines.extend(("", "Warnings:"))
    lines.extend(f"  - {warning}" for warning in view["warnings"])
    if not view["warnings"]:
        lines.append("  None")
    lines.extend(
        (
            "",
            "No prospective ledger written.",
            "No prospective evidence created.",
        )
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        snapshot = load_exploratory_snapshot(args.input)
        view = build_exploratory_price_view(snapshot)
    except ExploratoryPriceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(format_exploratory_price_view(view))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
