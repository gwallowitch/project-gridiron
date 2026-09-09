"""Run Gridiron from a game ID and six manually observed sportsbook prices."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.gridiron_operational_prediction import (
        OperationalPredictionError,
        build_operational_prediction,
        format_operational_prediction,
    )
except ModuleNotFoundError:  # Direct execution places scripts/ on sys.path.
    from gridiron_operational_prediction import (
        OperationalPredictionError,
        build_operational_prediction,
        format_operational_prediction,
    )

SCHEDULE_PATH = Path(
    "data/raw/schedules/step91i_schedules_2026_reg_weeks_01_16.json"
)
BOOK_ARGUMENTS = (
    ("BetMGM", "betmgm"),
    ("FanDuel", "fanduel"),
    ("DraftKings", "draftkings"),
)


class GameDayInputError(ValueError):
    """Game-day input cannot be resolved without guessing."""


def load_schedule(path: Path | str = SCHEDULE_PATH) -> tuple[dict[str, object], ...]:
    """Load the retained schedule and reject malformed or ambiguous identities."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise GameDayInputError(f"cannot read canonical schedule: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise GameDayInputError(f"invalid canonical schedule: {exc.msg}") from exc
    if not isinstance(value, list):
        raise GameDayInputError("canonical schedule must be an array")
    rows: list[dict[str, object]] = []
    identities: set[str] = set()
    for index, row in enumerate(value):
        if not isinstance(row, dict):
            raise GameDayInputError(f"canonical schedule row {index} must be an object")
        game_id = row.get("game_id")
        if not isinstance(game_id, str) or not game_id.strip():
            raise GameDayInputError(f"canonical schedule row {index} has no game_id")
        if game_id in identities:
            raise GameDayInputError(f"duplicate canonical game_id: {game_id}")
        identities.add(game_id)
        rows.append(row)
    return tuple(rows)


def resolve_game(
    game_id: str, schedule: tuple[dict[str, object], ...]
) -> dict[str, object]:
    """Resolve exactly one retained schedule row by canonical game ID."""
    if not game_id.strip():
        raise GameDayInputError("game_id must not be empty")
    matches = [row for row in schedule if row.get("game_id") == game_id]
    if len(matches) != 1:
        raise GameDayInputError(f"game_id not found in canonical schedule: {game_id}")
    game = matches[0]
    required = ("season", "week", "season_type", "home_team", "away_team", "kickoff_at")
    missing = [field for field in required if game.get(field) is None]
    if missing:
        raise GameDayInputError(
            "canonical schedule row is missing: " + ", ".join(missing)
        )
    return game


def build_game_day_snapshot(
    game: dict[str, object],
    prices: dict[str, tuple[int, int]],
    *,
    captured_at: datetime,
) -> dict[str, object]:
    """Create the existing operational snapshot shape with one observation time."""
    if captured_at.tzinfo is None:
        raise GameDayInputError("capture time must include a timezone")
    timestamp = captured_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    offers = []
    for book, _ in BOOK_ARGUMENTS:
        if book not in prices:
            raise GameDayInputError(f"missing prices for {book}")
        home_odds, away_odds = prices[book]
        offers.append(
            {
                "book": book,
                "home_odds": home_odds,
                "away_odds": away_odds,
                "observed_at": timestamp,
            }
        )
    return {
        "schema_version": 1,
        "provider": "manual-game-day-entry",
        "captured_at": timestamp,
        "game": {
            field: game[field]
            for field in (
                "game_id",
                "season",
                "season_type",
                "week",
                "kickoff_at",
                "home_team",
                "away_team",
            )
        },
        "offers": offers,
    }


def run_game_day(
    game_id: str,
    prices: dict[str, tuple[int, int]],
    *,
    def_epa: float,
    captured_at: datetime,
    schedule_path: Path | str = SCHEDULE_PATH,
) -> dict[str, object]:
    """Resolve, timestamp, and pass manual inputs to the existing runner."""
    game = resolve_game(game_id, load_schedule(schedule_path))
    snapshot = build_game_day_snapshot(game, prices, captured_at=captured_at)
    return build_operational_prediction(snapshot, def_epa=def_epa)


def _prompt_value(label: str, parser: Callable[[str], object]) -> object:
    try:
        return parser(input(f"{label}: ").strip())
    except (EOFError, ValueError) as exc:
        raise GameDayInputError(f"invalid {label.lower()}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", required=True, help="canonical 2026 game_id")
    parser.add_argument("--schedule", type=Path, default=SCHEDULE_PATH)
    for _, argument in BOOK_ARGUMENTS:
        parser.add_argument(f"--{argument}-home", type=int)
        parser.add_argument(f"--{argument}-away", type=int)
    parser.add_argument(
        "--def-epa",
        type=float,
        help="required caller-supplied def_epa_trend_advantage",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        game = resolve_game(args.game, load_schedule(args.schedule))
        print(
            f"Selected: {game['away_team']} @ {game['home_team']} | "
            f"kickoff {game['kickoff_at']}"
        )
        prices: dict[str, tuple[int, int]] = {}
        for book, argument in BOOK_ARGUMENTS:
            home = getattr(args, f"{argument}_home")
            away = getattr(args, f"{argument}_away")
            if home is None:
                home = _prompt_value(f"{book} home odds", int)
            if away is None:
                away = _prompt_value(f"{book} away odds", int)
            prices[book] = (home, away)
        def_epa = args.def_epa
        if def_epa is None:
            def_epa = _prompt_value("def_epa_trend_advantage", float)
        snapshot = build_game_day_snapshot(game, prices, captured_at=datetime.now(UTC))
        result = build_operational_prediction(snapshot, def_epa=def_epa)
    except (GameDayInputError, OperationalPredictionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    report = format_operational_prediction(result).replace(
        "Caller-supplied DEF EPA:",
        "DEF EPA (caller-supplied def_epa_trend_advantage):",
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
