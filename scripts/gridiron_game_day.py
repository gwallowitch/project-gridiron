"""Run Gridiron from a game ID and six manually observed sportsbook prices."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"

for import_root in (REPO_ROOT, SRC_ROOT):
    import_text = str(import_root)
    if import_text not in sys.path:
        sys.path.insert(0, import_text)

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

SCHEDULE_PATH = (
    REPO_ROOT
    / "data"
    / "raw"
    / "schedules"
    / "step91i_schedules_2026_reg_weeks_01_16.json"
)
BOOK_ARGUMENTS = (
    ("BetMGM", "betmgm"),
    ("FanDuel", "fanduel"),
    ("DraftKings", "draftkings"),
)


class GameDayInputError(ValueError):
    """Game-day input cannot be resolved without guessing."""


ODDS_API_URL = (
    "https://api.the-odds-api.com/v4/sports/"
    "americanfootball_nfl/odds/"
)

ODDS_API_BOOKS = {
    "betmgm": "BetMGM",
    "fanduel": "FanDuel",
    "draftkings": "DraftKings",
}

NFL_TEAM_NAMES = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LA": "Los Angeles Rams",
    "LAC": "Los Angeles Chargers",
    "LV": "Las Vegas Raiders",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}


def _fetch_json(url: str) -> object:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ProjectGridiron/1.0",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise GameDayInputError(
            f"live odds fetch failed: HTTP {exc.code}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise GameDayInputError(f"live odds fetch failed: {exc}") from exc


def _team_name(abbreviation: object) -> str:
    if not isinstance(abbreviation, str):
        raise GameDayInputError("canonical team abbreviation must be a string")
    try:
        return NFL_TEAM_NAMES[abbreviation]
    except KeyError as exc:
        raise GameDayInputError(
            f"no Odds API team mapping for {abbreviation}"
        ) from exc


def _american_price(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GameDayInputError(f"{field} must be numeric")
    if int(value) != value:
        raise GameDayInputError(f"{field} must be an integer American price")
    price = int(value)
    if -100 < price < 100:
        raise GameDayInputError(
            f"{field} must be <= -100 or >= +100"
        )
    return price


def fetch_live_prices(
    game: dict[str, object],
) -> tuple[dict[str, tuple[int, int]], dict[str, str]]:
    """Fetch all three operational books using one Odds API request."""
    api_key = os.environ.get("GRIDIRON_ODDS_API_KEY")
    if not api_key:
        raise GameDayInputError(
            "GRIDIRON_ODDS_API_KEY is not set"
        )

    query = (
        f"?apiKey={api_key}"
        "&regions=us"
        "&markets=h2h"
        "&oddsFormat=american"
        "&bookmakers=draftkings,fanduel,betmgm"
    )
    payload = _fetch_json(ODDS_API_URL + query)

    if not isinstance(payload, list):
        raise GameDayInputError("invalid Odds API response")

    expected_home = _team_name(game["home_team"])
    expected_away = _team_name(game["away_team"])

    matches = [
        event
        for event in payload
        if isinstance(event, dict)
        and event.get("home_team") == expected_home
        and event.get("away_team") == expected_away
    ]

    if len(matches) != 1:
        raise GameDayInputError(
            "could not uniquely resolve requested game in live odds feed"
        )

    event = matches[0]
    bookmakers = event.get("bookmakers")
    if not isinstance(bookmakers, list):
        raise GameDayInputError("live game has no bookmaker list")

    prices: dict[str, tuple[int, int]] = {}
    observed_at: dict[str, str] = {}

    for bookmaker in bookmakers:
        if not isinstance(bookmaker, dict):
            continue

        key = bookmaker.get("key")
        if key not in ODDS_API_BOOKS:
            continue

        book = ODDS_API_BOOKS[key]
        markets = bookmaker.get("markets")
        if not isinstance(markets, list):
            continue

        h2h = next(
            (
                market
                for market in markets
                if isinstance(market, dict)
                and market.get("key") == "h2h"
            ),
            None,
        )
        if h2h is None:
            continue

        outcomes = h2h.get("outcomes")
        if not isinstance(outcomes, list):
            continue

        by_team = {
            outcome.get("name"): outcome.get("price")
            for outcome in outcomes
            if isinstance(outcome, dict)
        }

        if expected_home not in by_team or expected_away not in by_team:
            continue

        home_price = _american_price(
            by_team[expected_home],
            f"{book} home odds",
        )
        away_price = _american_price(
            by_team[expected_away],
            f"{book} away odds",
        )

        last_update = bookmaker.get("last_update")
        if not isinstance(last_update, str) or not last_update:
            raise GameDayInputError(
                f"{book} live odds are missing last_update"
            )

        prices[book] = (home_price, away_price)
        observed_at[book] = last_update

    missing = [
        book
        for book, _ in BOOK_ARGUMENTS
        if book not in prices
    ]
    if missing:
        raise GameDayInputError(
            "live odds feed missing required books: "
            + ", ".join(missing)
        )

    return prices, observed_at


def frozen_def_epa_for_game(game: dict[str, object]) -> float | None:
    """Return only frozen protocol-defined automatic DEF EPA values."""
    if game.get("season_type") == "REG" and int(game["week"]) == 1:
        return 0.0
    return None


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
    observed_at: dict[str, str] | None = None,
) -> dict[str, object]:
    """Create the existing operational snapshot shape."""
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
                "observed_at": (
                    observed_at.get(book, timestamp)
                    if observed_at is not None
                    else timestamp
                ),
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
        supplied_prices = {}
        complete_manual = True
        for book, argument in BOOK_ARGUMENTS:
            home = getattr(args, f"{argument}_home")
            away = getattr(args, f"{argument}_away")
            if home is None or away is None:
                complete_manual = False
                break
            supplied_prices[book] = (home, away)

        observed_at = None
        if complete_manual:
            prices = supplied_prices
            print("Odds source: explicit CLI values")
        else:
            print(
                "Fetching live BetMGM / FanDuel / "
                "DraftKings moneylines..."
            )
            prices, observed_at = fetch_live_prices(game)
            print("Live odds:")
            for book, _ in BOOK_ARGUMENTS:
                home, away = prices[book]
                print(
                    f"  {book}: home {home:+d} / "
                    f"away {away:+d} "
                    f"[{observed_at[book]}]"
                )

        def_epa = args.def_epa
        if def_epa is None:
            def_epa = frozen_def_epa_for_game(game)
        if def_epa is None:
            def_epa = _prompt_value("def_epa_trend_advantage", float)
        else:
            print(f"DEF EPA: {def_epa:+.6f} (frozen Week 1 neutral rule)")
        snapshot = build_game_day_snapshot(
            game,
            prices,
            captured_at=datetime.now(UTC),
            observed_at=observed_at,
        )
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
