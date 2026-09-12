"""Collect predetermined non-prospective operational market observations."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for import_root in (REPO_ROOT, SRC_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from gridiron.market.collection_attempts import (
    CollectionAttemptError,
    append_collection_attempt,
    build_collection_attempt,
    read_collection_attempts,
)
from gridiron.market.operational_history import (
    OperationalHistoryError,
    append_operational_observation,
    read_operational_history,
)
from scripts import gridiron_game_day as game_day
from scripts.gridiron_operational_prediction import OperationalPredictionError

ATTEMPT_PATH = REPO_ROOT / "data" / "operational" / "collection_attempts_v1.jsonl"
HISTORY_PATH = game_day.HISTORY_PATH
SCHEDULE_PATH = game_day.SCHEDULE_PATH
AUTOMATIC_PROVIDER_PREFIX = "the-odds-api-operational-step91q:"


@dataclass(frozen=True)
class CollectionWindow:
    label: str
    target_minutes: int
    minimum_minutes: int
    maximum_minutes: int


WINDOWS = (
    CollectionWindow("T12H", 720, 660, 780),
    CollectionWindow("T6H", 360, 330, 390),
    CollectionWindow("T3H", 180, 150, 210),
    CollectionWindow("T1H", 60, 45, 75),
    CollectionWindow("NEAR_KICKOFF", 15, 5, 30),
)


@dataclass(frozen=True)
class CollectionOutcome:
    game_id: str
    target: str
    result: str
    reason_code: str
    actual_minutes: float
    observation_id: str | None = None


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise game_day.GameDayInputError("kickoff_at must be an ISO-8601 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise game_day.GameDayInputError("kickoff_at must include a timezone")
    return parsed.astimezone(UTC)


def eligible_window(minutes_to_kickoff: float) -> CollectionWindow | None:
    """Return the one fixed collection window containing actual timing."""
    return next(
        (
            window
            for window in WINDOWS
            if window.minimum_minutes <= minutes_to_kickoff <= window.maximum_minutes
        ),
        None,
    )


def _automatic_provider(target: str) -> str:
    return AUTOMATIC_PROVIDER_PREFIX + target


def _automatic_observations(
    history: tuple[dict[str, Any], ...],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Index only rows carrying exact Step 91Q target provenance."""
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    windows = {window.label: window for window in WINDOWS}
    for row in history:
        provider = row.get("provider")
        if not isinstance(provider, str) or not provider.startswith(
            AUTOMATIC_PROVIDER_PREFIX
        ):
            continue
        target = provider.removeprefix(AUTOMATIC_PROVIDER_PREFIX)
        if target not in windows:
            raise CollectionAttemptError("invalid Step 91Q provider target marker")
        game = row["game"]
        timing = row["timing"]
        key = (game["game_id"], target)
        actual = float(timing["minutes_to_kickoff"])
        window = windows[target]
        if not window.minimum_minutes <= actual <= window.maximum_minutes:
            raise CollectionAttemptError(
                "Step 91Q observation target marker is outside its window"
            )
        if key in indexed:
            raise CollectionAttemptError("duplicate Step 91Q target observations")
        indexed[key] = row
    return indexed


def _attempt_log_still_trustworthy(path: Path | str) -> None:
    """Revalidate retained attempt evidence after a bounded append failure."""
    read_collection_attempts(path)


def _reason_code(exc: Exception) -> str:
    message = str(exc).lower()
    if "def epa" in message or "nflverse" in message or "prior week" in message:
        return "DEF_EPA_UNAVAILABLE"
    if "missing" in message and any(book.lower() in message for book in game_day.ODDS_API_BOOKS.values()):
        return "MISSING_BOOK"
    if "stale" in message:
        return "STALE_PRICE"
    if "timestamp" in message:
        return "INVALID_TIMESTAMP"
    if "odds" in message or "api" in message or "live game" in message:
        return "ODDS_PROVIDER_ERROR"
    if isinstance(exc, OperationalHistoryError):
        return "HISTORY_APPEND_FAILED"
    return "OPERATIONAL_VALIDATION_FAILED"


def _attempt(
    game: dict[str, object],
    window: CollectionWindow,
    now: datetime,
    result: str,
    reason: str,
    observation_id: str | None = None,
) -> dict[str, Any]:
    return build_collection_attempt(
        game_id=str(game["game_id"]),
        collection_target=window.label,
        target_minutes_to_kickoff=window.target_minutes,
        kickoff_at=str(game["kickoff_at"]),
        attempted_at=now,
        result=result,
        reason_code=reason,
        observation_id=observation_id,
    )


def collect(
    *,
    now: datetime,
    schedule_path: Path | str = SCHEDULE_PATH,
    history_path: Path | str = HISTORY_PATH,
    attempt_path: Path | str = ATTEMPT_PATH,
    game_id: str | None = None,
    dry_run: bool = False,
    price_fetcher: Callable[[dict[str, object]], tuple[dict[str, tuple[int, int]], dict[str, str]]] = game_day.fetch_live_prices,
    def_epa_loader: Callable[[dict[str, object]], float] = game_day.automatic_def_epa_for_game,
) -> tuple[CollectionOutcome, ...]:
    """Process all locally eligible targets once using existing operational code."""
    if now.tzinfo is None:
        raise game_day.GameDayInputError("collector time must include a timezone")
    now = now.astimezone(UTC)
    history = read_operational_history(history_path)
    attempts = read_collection_attempts(attempt_path)
    automatic_observations = _automatic_observations(history)
    observation_ids = {item["observation_id"] for item in history}
    for attempt in attempts:
        linked = attempt.get("observation_id")
        if attempt["result"] == "SUCCESS" and linked not in observation_ids:
            raise CollectionAttemptError("successful attempt links missing observation")
        if attempt["result"] == "SUCCESS":
            key = (attempt["game_id"], attempt["collection_target"])
            automatic = automatic_observations.get(key)
            if automatic is None or automatic["observation_id"] != linked:
                raise CollectionAttemptError(
                    "successful attempt lacks matching Step 91Q observation provenance"
                )
    prior = {(item["game_id"], item["collection_target"]): item for item in attempts}
    schedule = game_day.load_schedule(schedule_path)
    if game_id is not None:
        schedule = (game_day.resolve_game(game_id, schedule),)

    outcomes: list[CollectionOutcome] = []
    for game in schedule:
        kickoff = _parse_timestamp(game["kickoff_at"])
        minutes = (kickoff - now).total_seconds() / 60.0
        game_key = str(game["game_id"])
        recovery_keys: set[tuple[str, str]] = set()
        for window in WINDOWS:
            key = (game_key, window.label)
            orphan = automatic_observations.get(key)
            if orphan is None or key in prior:
                continue
            recovery_keys.add(key)
            collected_at = _parse_timestamp(orphan["timing"]["collected_at"])
            if dry_run:
                outcomes.append(
                    CollectionOutcome(
                        game_key,
                        window.label,
                        "RECOVERY_REQUIRED",
                        "RECOVERED_SUCCESS",
                        float(orphan["timing"]["minutes_to_kickoff"]),
                        orphan["observation_id"],
                    )
                )
                continue
            record = _attempt(
                game,
                window,
                collected_at,
                "SUCCESS",
                "RECOVERED_SUCCESS",
                orphan["observation_id"],
            )
            try:
                append_collection_attempt(attempt_path, record)
            except (CollectionAttemptError, OSError):
                _attempt_log_still_trustworthy(attempt_path)
                outcomes.append(
                    CollectionOutcome(
                        game_key,
                        window.label,
                        "FAILED",
                        "ATTEMPT_LOG_APPEND_FAILED",
                        float(orphan["timing"]["minutes_to_kickoff"]),
                        orphan["observation_id"],
                    )
                )
                continue
            prior[key] = record
            outcomes.append(
                CollectionOutcome(
                    game_key,
                    window.label,
                    "SUCCESS",
                    "RECOVERED_SUCCESS",
                    float(orphan["timing"]["minutes_to_kickoff"]),
                    orphan["observation_id"],
                )
            )
        if minutes <= 0.0:
            outcomes.append(
                CollectionOutcome(str(game["game_id"]), "-", "POST_KICKOFF", "POST_KICKOFF", minutes)
            )
            continue
        current = eligible_window(minutes)
        for window in WINDOWS:
            key = (game_key, window.label)
            if key in recovery_keys:
                continue
            existing = prior.get(key)
            if existing is not None:
                label = "ALREADY_COMPLETE" if existing["result"] == "SUCCESS" else "DUPLICATE_TARGET"
                outcomes.append(CollectionOutcome(str(game["game_id"]), window.label, label, str(existing["reason_code"]), minutes, existing.get("observation_id")))
                continue
            if minutes < window.minimum_minutes:
                record = _attempt(game, window, now, "SKIPPED_OUTSIDE_WINDOW", "MISSED_WINDOW")
                outcomes.append(CollectionOutcome(str(game["game_id"]), window.label, "MISSED_WINDOW", "MISSED_WINDOW", minutes))
                if not dry_run:
                    try:
                        append_collection_attempt(attempt_path, record)
                    except (CollectionAttemptError, OSError):
                        _attempt_log_still_trustworthy(attempt_path)
                        outcomes[-1] = CollectionOutcome(
                            game_key,
                            window.label,
                            "FAILED",
                            "ATTEMPT_LOG_APPEND_FAILED",
                            minutes,
                        )
                        continue
                    prior[key] = record
                continue
            if current != window:
                continue
            if dry_run:
                outcomes.append(CollectionOutcome(str(game["game_id"]), window.label, "DRY_RUN_ELIGIBLE", "SUCCESS", minutes))
                continue
            try:
                def_epa = def_epa_loader(game)
                def_epa_source = (
                    "frozen Week 1 neutral rule"
                    if int(game["week"]) == 1
                    else "automatic nflverse frozen feature"
                )
                prices, observed_at = price_fetcher(game)
                snapshot = game_day.build_game_day_snapshot(
                    game,
                    prices,
                    captured_at=now,
                    observed_at=observed_at,
                    provider=_automatic_provider(window.label),
                )
                prediction = game_day.build_operational_prediction(
                    snapshot, def_epa=def_epa, def_epa_source=def_epa_source
                )
                observation = append_operational_observation(history_path, prediction)
                record = _attempt(
                    game, window, now, "SUCCESS", "SUCCESS", observation["observation_id"]
                )
                try:
                    append_collection_attempt(attempt_path, record)
                except (CollectionAttemptError, OSError):
                    _attempt_log_still_trustworthy(attempt_path)
                    outcomes.append(
                        CollectionOutcome(
                            game_key,
                            window.label,
                            "FAILED",
                            "ATTEMPT_LOG_APPEND_FAILED",
                            minutes,
                            observation["observation_id"],
                        )
                    )
                    continue
                prior[key] = record
                outcomes.append(CollectionOutcome(str(game["game_id"]), window.label, "SUCCESS", "SUCCESS", minutes, observation["observation_id"]))
            except (game_day.GameDayInputError, OperationalPredictionError, OperationalHistoryError) as exc:
                reason = _reason_code(exc)
                record = _attempt(game, window, now, "FAILED", reason)
                try:
                    append_collection_attempt(attempt_path, record)
                except (CollectionAttemptError, OSError):
                    _attempt_log_still_trustworthy(attempt_path)
                    outcomes.append(
                        CollectionOutcome(
                            game_key,
                            window.label,
                            "FAILED",
                            "ATTEMPT_LOG_APPEND_FAILED",
                            minutes,
                        )
                    )
                    continue
                prior[key] = record
                outcomes.append(CollectionOutcome(str(game["game_id"]), window.label, "FAILED", reason, minutes))
    return tuple(outcomes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--game")
    parser.add_argument("--schedule", type=Path, default=SCHEDULE_PATH)
    parser.add_argument("--history-path", type=Path, default=HISTORY_PATH)
    parser.add_argument("--attempt-path", type=Path, default=ATTEMPT_PATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print("PROJECT GRIDIRON — OPERATIONAL MARKET COLLECTOR")
    print("NON-PROSPECTIVE DATA COLLECTION\n")
    try:
        outcomes = collect(
            now=datetime.now(UTC),
            schedule_path=args.schedule,
            history_path=args.history_path,
            attempt_path=args.attempt_path,
            game_id=args.game,
            dry_run=args.dry_run,
        )
    except (CollectionAttemptError, OperationalHistoryError, game_day.GameDayInputError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for item in outcomes:
        print(f"{item.game_id} | {item.target} | {item.result} | {item.reason_code}")
        if item.observation_id:
            print(f"  Observation: {item.observation_id}")
    print(f"\nSummary: {len(outcomes)} classified targets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
