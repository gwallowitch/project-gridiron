"""Collect three-book NFL totals as non-prospective observations."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from gridiron.market.operational_totals import (
    AUTOMATIC_PROVIDER_PREFIX,
    TARGET_WINDOWS,
    OperationalTotalsError,
    append_totals_observation,
    build_totals_observation,
    parse_timestamp,
    parse_totals_payload,
    read_totals_history,
)
from gridiron.market.totals_collection_attempts import (
    TotalsAttemptError,
    append_totals_attempt,
    build_totals_attempt,
    read_totals_attempts,
)
from scripts import gridiron_game_day as game_day

SCHEDULE_PATH = game_day.SCHEDULE_PATH
HISTORY_PATH = REPO_ROOT / "data" / "operational" / "totals_history_v1.jsonl"
ATTEMPT_PATH = REPO_ROOT / "data" / "operational" / "totals_collection_attempts_v1.jsonl"
ODDS_URL = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"


def eligible_target(minutes: float) -> str | None:
    return next((label for label, (_, low, high) in TARGET_WINDOWS.items() if low <= minutes <= high), None)


def fetch_live_totals_payload() -> object:
    """Fetch one totals payload without selecting a scheduled game."""
    try:
        key = game_day.validated_odds_api_key()
    except game_day.GameDayInputError as exc:
        raise OperationalTotalsError(str(exc)) from exc
    query = urllib.parse.urlencode(
        {
            "apiKey": key,
            "regions": "us",
            "markets": "totals",
            "oddsFormat": "american",
            "bookmakers": "draftkings,fanduel,betmgm",
        }
    )
    url = f"{ODDS_URL}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "ProjectGridiron/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise OperationalTotalsError("totals provider request failed") from exc
    return payload


def parse_live_totals(
    payload: object, game: dict[str, object], collected_at: datetime
) -> tuple[dict[str, Any], ...]:
    """Parse one scheduled game from an already fetched totals payload."""
    return parse_totals_payload(
        payload,
        home_name=game_day.NFL_TEAM_NAMES[str(game["home_team"])],
        away_name=game_day.NFL_TEAM_NAMES[str(game["away_team"])],
        collected_at=collected_at,
    )


def fetch_live_totals(game: dict[str, object], collected_at: datetime) -> tuple[dict[str, Any], ...]:
    """Make exactly one live totals request for one eligible game."""
    return parse_live_totals(fetch_live_totals_payload(), game, collected_at)


def _automatic(history: tuple[dict[str, Any], ...]) -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in history:
        provider = row["provider"]
        if not provider.startswith(AUTOMATIC_PROVIDER_PREFIX):
            continue
        target = provider.removeprefix(AUTOMATIC_PROVIDER_PREFIX)
        key = (row["game"]["game_id"], target)
        if key in rows:
            raise OperationalTotalsError("contradictory automatic totals observations")
        rows[key] = row
    return rows


def _reason(exc: Exception) -> str:
    text = str(exc).lower()
    if "missing" in text or "required totals books" in text:
        return "MISSING_BOOK"
    if "stale" in text:
        return "STALE_PRICE"
    if "timestamp" in text:
        return "INVALID_TIMESTAMP"
    if "market" in text or "over" in text or "under" in text or "point" in text:
        return "MALFORMED_TOTALS_MARKET"
    if "provider" in text or "api" in text:
        return "PROVIDER_ERROR"
    return "OPERATIONAL_VALIDATION_FAILED"


def collect(
    *, now: datetime, schedule_path: Path | str = SCHEDULE_PATH,
    history_path: Path | str = HISTORY_PATH, attempt_path: Path | str = ATTEMPT_PATH,
    game_id: str | None = None, dry_run: bool = False,
    fetcher: Callable[[dict[str, object], datetime], tuple[dict[str, Any], ...]] = fetch_live_totals,
) -> tuple[dict[str, Any], ...]:
    if now.tzinfo is None:
        raise OperationalTotalsError("now must include a timezone")
    now = now.astimezone(UTC)
    history = read_totals_history(history_path)
    attempts = read_totals_attempts(attempt_path)
    automatic = _automatic(history)
    by_id = {row["observation_id"]: row for row in history}
    prior = {(row["game_id"], row["target_label"]): row for row in attempts}
    for row in attempts:
        if row["result"] == "SUCCESS":
            linked = by_id.get(row["observation_id"])
            key = (row["game_id"], row["target_label"])
            if (
                linked is None
                or automatic.get(key) != linked
                or row["attempted_at"] != linked["timing"]["collected_at"]
                or row["kickoff_at"] != linked["game"]["kickoff_at"]
            ):
                raise TotalsAttemptError("successful totals attempt linkage is invalid")
    schedule = game_day.load_schedule(schedule_path)
    if game_id:
        schedule = (game_day.resolve_game(game_id, schedule),)
    output: list[dict[str, Any]] = []
    for game in schedule:
        kickoff = parse_timestamp(game["kickoff_at"], "kickoff_at")
        minutes = (kickoff - now).total_seconds() / 60
        game_key = str(game["game_id"])
        recovered: set[tuple[str, str]] = set()
        for target in TARGET_WINDOWS:
            key = (game_key, target)
            orphan = automatic.get(key)
            if orphan is None or key in prior:
                continue
            recovered.add(key)
            if dry_run:
                output.append({"game_id": game_key, "target": target, "result": "RECOVERY_REQUIRED"})
                continue
            expected_game = {
                field: game[field]
                for field in (
                    "game_id", "season", "week", "season_type", "home_team", "away_team",
                )
            }
            expected_game["kickoff_at"] = kickoff.isoformat().replace("+00:00", "Z")
            if orphan["game"] != expected_game:
                raise OperationalTotalsError("orphan totals observation does not match schedule")
            attempted = parse_timestamp(orphan["timing"]["collected_at"], "collected_at")
            record = build_totals_attempt(game_id=game_key, target_label=target, kickoff_at=str(game["kickoff_at"]), attempted_at=attempted, result="SUCCESS", reason_code="RECOVERED_SUCCESS", observation_id=orphan["observation_id"])
            try:
                append_totals_attempt(attempt_path, record)
            except (TotalsAttemptError, OSError):
                read_totals_attempts(attempt_path)
                output.append({"game_id": game_key, "target": target, "result": "FAILED", "reason": "ATTEMPT_LOG_APPEND_FAILED"})
                continue
            prior[key] = record
            output.append({"game_id": game_key, "target": target, "result": "SUCCESS", "reason": "RECOVERED_SUCCESS", "observation_id": orphan["observation_id"]})
        if minutes <= 0:
            output.append({"game_id": game_key, "target": None, "result": "POST_KICKOFF"})
            continue
        current = eligible_target(minutes)
        for target, (_, low, _) in TARGET_WINDOWS.items():
            key = (game_key, target)
            if key in recovered:
                continue
            if key in prior:
                output.append({"game_id": game_key, "target": target, "result": "ALREADY_ATTEMPTED"})
                continue
            if minutes < low:
                output.append({"game_id": game_key, "target": target, "result": "MISSED_WINDOW"})
                if not dry_run:
                    record = build_totals_attempt(game_id=game_key, target_label=target, kickoff_at=str(game["kickoff_at"]), attempted_at=now, result="MISSED_WINDOW", reason_code="MISSED_WINDOW")
                    append_totals_attempt(attempt_path, record)
                    prior[key] = record
                continue
            if current != target:
                continue
            if dry_run:
                output.append({"game_id": game_key, "target": target, "result": "DRY_RUN_ELIGIBLE"})
                continue
            try:
                books = fetcher(game, now)
                observation = build_totals_observation(game, books, collected_at=now, target_label=target, provider=AUTOMATIC_PROVIDER_PREFIX + target)
                append_totals_observation(history_path, observation)
                attempt = build_totals_attempt(game_id=game_key, target_label=target, kickoff_at=str(game["kickoff_at"]), attempted_at=now, result="SUCCESS", reason_code="SUCCESS", observation_id=observation["observation_id"])
                try:
                    append_totals_attempt(attempt_path, attempt)
                except (TotalsAttemptError, OSError):
                    read_totals_attempts(attempt_path)
                    output.append({"game_id": game_key, "target": target, "result": "FAILED", "reason": "ATTEMPT_LOG_APPEND_FAILED"})
                    continue
                prior[key] = attempt
                output.append({"game_id": game_key, "target": target, "result": "SUCCESS", "observation_id": observation["observation_id"]})
            except OperationalTotalsError as exc:
                reason = _reason(exc)
                attempt = build_totals_attempt(game_id=game_key, target_label=target, kickoff_at=str(game["kickoff_at"]), attempted_at=now, result="FAILED", reason_code=reason)
                try:
                    append_totals_attempt(attempt_path, attempt)
                except (TotalsAttemptError, OSError):
                    output.append({"game_id": game_key, "target": target, "result": "FAILED", "reason": "ATTEMPT_LOG_APPEND_FAILED"})
                else:
                    prior[key] = attempt
                    output.append({"game_id": game_key, "target": target, "result": "FAILED", "reason": reason})
            except OSError:
                attempt = build_totals_attempt(game_id=game_key, target_label=target, kickoff_at=str(game["kickoff_at"]), attempted_at=now, result="FAILED", reason_code="HISTORY_APPEND_FAILED")
                try:
                    append_totals_attempt(attempt_path, attempt)
                except (TotalsAttemptError, OSError):
                    output.append({"game_id": game_key, "target": target, "result": "FAILED", "reason": "ATTEMPT_LOG_APPEND_FAILED"})
                else:
                    prior[key] = attempt
                    output.append({"game_id": game_key, "target": target, "result": "FAILED", "reason": "HISTORY_APPEND_FAILED"})
    return tuple(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--game")
    parser.add_argument("--schedule", type=Path, default=SCHEDULE_PATH)
    parser.add_argument("--history-path", type=Path, default=HISTORY_PATH)
    parser.add_argument("--attempt-path", type=Path, default=ATTEMPT_PATH)
    args = parser.parse_args(argv)
    try:
        rows = collect(now=datetime.now(UTC), schedule_path=args.schedule, history_path=args.history_path, attempt_path=args.attempt_path, game_id=args.game, dry_run=args.dry_run)
    except (OperationalTotalsError, TotalsAttemptError, game_day.GameDayInputError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("PROJECT GRIDIRON — NON-PROSPECTIVE TOTALS COLLECTION")
    for row in rows:
        print(f"{row['game_id']} | {row['target']} | {row['result']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
