"""Read-only Step 91V moneyline and totals collection coverage audit."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from gridiron.market.collection_attempts import (
    CollectionAttemptError,
    read_collection_attempts,
)
from gridiron.market.operational_history import (
    OperationalHistoryError,
    read_operational_history,
)
from gridiron.market.operational_totals import (
    AUTOMATIC_PROVIDER_PREFIX as TOTALS_PROVIDER_PREFIX,
)
from gridiron.market.operational_totals import (
    TARGET_WINDOWS,
    OperationalTotalsError,
    read_totals_history,
)
from gridiron.market.totals_collection_attempts import (
    TotalsAttemptError,
    read_totals_attempts,
)
from scripts import gridiron_game_day as game_day
from scripts.gridiron_market_collector import (
    ATTEMPT_PATH as MONEYLINE_ATTEMPT_PATH,
)
from scripts.gridiron_market_collector import (
    AUTOMATIC_PROVIDER_PREFIX as MONEYLINE_PROVIDER_PREFIX,
)
from scripts.gridiron_market_collector import (
    HISTORY_PATH as MONEYLINE_HISTORY_PATH,
)
from scripts.gridiron_market_collector import (
    WINDOWS,
)
from scripts.gridiron_totals_collector import (
    ATTEMPT_PATH as TOTALS_ATTEMPT_PATH,
)
from scripts.gridiron_totals_collector import (
    HISTORY_PATH as TOTALS_HISTORY_PATH,
)

CLASSIFICATION = "READ_ONLY_NON_PROSPECTIVE_COLLECTION_HEALTH"
TARGET_ORDER = tuple(window.label for window in WINDOWS)
WINDOW_BY_TARGET = {
    window.label: (
        window.target_minutes,
        window.minimum_minutes,
        window.maximum_minutes,
    )
    for window in WINDOWS
}
if WINDOW_BY_TARGET != TARGET_WINDOWS:
    raise RuntimeError("moneyline and totals frozen target windows disagree")


class CollectionHealthError(ValueError):
    """Operational evidence or schedule data cannot be audited safely."""


@dataclass(frozen=True)
class LaneEvidence:
    observations: Mapping[tuple[str, str], Mapping[str, Any]]
    attempts: Mapping[tuple[str, str], Mapping[str, Any]]


def _validate_canonical_evidence(
    schedule: Sequence[Mapping[str, Any]], *lanes: LaneEvidence
) -> None:
    canonical = {str(game["game_id"]): game for game in schedule}
    for lane in lanes:
        for (game_id, _), row in lane.observations.items():
            game = row["game"]
            expected = canonical.get(game_id)
            if expected is None:
                raise CollectionHealthError("operational history contains an unknown game")
            for field in ("season", "week", "season_type", "home_team", "away_team", "kickoff_at"):
                if game.get(field) != expected.get(field):
                    raise CollectionHealthError(f"operational history canonical {field} mismatch")
        for (game_id, _), attempt in lane.attempts.items():
            expected = canonical.get(game_id)
            if expected is None:
                raise CollectionHealthError("attempt history contains an unknown game")
            if attempt.get("kickoff_at") != expected.get("kickoff_at"):
                raise CollectionHealthError("attempt history canonical kickoff mismatch")


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise CollectionHealthError(f"{field} must be an ISO-8601 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise CollectionHealthError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise CollectionHealthError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _automatic_observations(
    history: Sequence[Mapping[str, Any]], *, prefix: str, totals: bool
) -> dict[tuple[str, str], Mapping[str, Any]]:
    indexed: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in history:
        provider = row.get("provider")
        if not isinstance(provider, str) or not provider.startswith(prefix):
            continue
        target = provider.removeprefix(prefix)
        if target not in WINDOW_BY_TARGET:
            raise CollectionHealthError("automatic observation has an unknown target")
        game = row.get("game")
        timing = row.get("timing")
        if not isinstance(game, Mapping) or not isinstance(timing, Mapping):
            raise CollectionHealthError("automatic observation structure is invalid")
        minutes_field = "minutes_before_kickoff" if totals else "minutes_to_kickoff"
        minutes = timing.get(minutes_field)
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)):
            raise CollectionHealthError("automatic observation timing is invalid")
        _, low, high = WINDOW_BY_TARGET[target]
        if not low <= float(minutes) <= high:
            raise CollectionHealthError("automatic observation is outside its target window")
        key = (str(game.get("game_id")), target)
        if key in indexed:
            raise CollectionHealthError("duplicate automatic target observation")
        indexed[key] = row
    return indexed


def _lane_evidence(
    history: Sequence[Mapping[str, Any]],
    attempts: Sequence[Mapping[str, Any]],
    *,
    prefix: str,
    totals: bool,
) -> LaneEvidence:
    observations = _automatic_observations(history, prefix=prefix, totals=totals)
    indexed_attempts: dict[tuple[str, str], Mapping[str, Any]] = {}
    by_id = {row["observation_id"]: row for row in history}
    for attempt in attempts:
        target_field = "target_label" if totals else "collection_target"
        key = (str(attempt["game_id"]), str(attempt[target_field]))
        indexed_attempts[key] = attempt
        if attempt["result"] != "SUCCESS":
            continue
        observation = by_id.get(attempt["observation_id"])
        if observation is None or observations.get(key) != observation:
            raise CollectionHealthError("successful attempt lacks its automatic history row")
        if attempt["kickoff_at"] != observation["game"]["kickoff_at"]:
            raise CollectionHealthError("successful attempt/history kickoff mismatch")
        if attempt["attempted_at"] != observation["timing"]["collected_at"]:
            raise CollectionHealthError("successful attempt/history timestamp mismatch")
    return LaneEvidence(observations, indexed_attempts)


def _target_state(
    game_id: str,
    target: str,
    minutes_to_kickoff: float,
    evidence: LaneEvidence,
) -> dict[str, Any]:
    key = (game_id, target)
    observation = evidence.observations.get(key)
    attempt = evidence.attempts.get(key)
    if observation is not None and attempt is None:
        return {"state": "RECOVERY_REQUIRED", "reason": "HISTORY_WITHOUT_ATTEMPT"}
    if observation is not None and attempt is not None:
        if attempt["result"] != "SUCCESS" or attempt["observation_id"] != observation["observation_id"]:
            return {"state": "INVALID_EVIDENCE", "reason": "ATTEMPT_HISTORY_DISAGREE"}
        return {"state": "SUCCESS", "reason": attempt["reason_code"], "observation_id": observation["observation_id"]}
    if attempt is not None:
        result = attempt["result"]
        reason = attempt["reason_code"]
        if result == "SUCCESS":
            return {"state": "INVALID_EVIDENCE", "reason": "SUCCESS_WITHOUT_HISTORY"}
        if reason == "MISSED_WINDOW" or result in {"MISSED_WINDOW", "SKIPPED_OUTSIDE_WINDOW"}:
            return {"state": "MISSED_WINDOW", "reason": reason}
        if result == "POST_KICKOFF":
            return {"state": "POST_KICKOFF_NO_SUCCESS", "reason": reason}
        if result == "FAILED":
            actual = attempt.get(
                "actual_minutes_before_kickoff",
                attempt.get("actual_minutes_to_kickoff"),
            )
            _, low, high = WINDOW_BY_TARGET[target]
            if not isinstance(actual, (int, float)) or isinstance(actual, bool) or not low <= float(actual) <= high:
                return {"state": "INVALID_EVIDENCE", "reason": "FAILURE_OUTSIDE_TARGET_WINDOW"}
            return {"state": "FAILED_IN_WINDOW", "reason": reason}
        return {"state": "INVALID_EVIDENCE", "reason": "UNSUPPORTED_ATTEMPT_STATE"}
    _, low, high = WINDOW_BY_TARGET[target]
    if minutes_to_kickoff > high:
        return {"state": "NOT_YET_DUE", "reason": "FUTURE_WINDOW"}
    if low <= minutes_to_kickoff <= high:
        return {"state": "IN_WINDOW_PENDING", "reason": "NO_ATTEMPT_OBSERVED"}
    if minutes_to_kickoff > 0:
        return {"state": "WINDOW_EXPIRED_NO_SUCCESS", "reason": "NO_ATTEMPT_OBSERVED"}
    return {"state": "POST_KICKOFF_NO_SUCCESS", "reason": "NO_ATTEMPT_OBSERVED"}


def _lane_report(
    game_id: str,
    minutes: float,
    evidence: LaneEvidence,
) -> dict[str, Any]:
    targets = {target: _target_state(game_id, target, minutes, evidence) for target in TARGET_ORDER}
    states = [item["state"] for item in targets.values()]
    due = sum(state != "NOT_YET_DUE" for state in states)
    success = states.count("SUCCESS")
    invalid = states.count("INVALID_EVIDENCE")
    recovery = states.count("RECOVERY_REQUIRED")
    pending = states.count("IN_WINDOW_PENDING")
    failed = states.count("FAILED_IN_WINDOW")
    missed = sum(state in {"MISSED_WINDOW", "WINDOW_EXPIRED_NO_SUCCESS", "POST_KICKOFF_NO_SUCCESS"} for state in states)
    if invalid:
        overall = "INVALID"
    elif recovery or pending:
        overall = "ACTION_NEEDED"
    elif failed or missed:
        overall = "DEGRADED"
    elif due == 0:
        overall = "NOT_YET_ACTIVE"
    elif minutes <= 0 and success == len(TARGET_ORDER):
        overall = "GAME_COMPLETE"
    else:
        overall = "HEALTHY"
    successful_rows = [
        evidence.observations[(game_id, target)]
        for target in TARGET_ORDER
        if targets[target]["state"] == "SUCCESS"
    ]
    latest = max(successful_rows, key=lambda row: row["timing"]["collected_at"], default=None)
    return {
        "overall": overall,
        "successful_target_count": success,
        "expected_due_target_count": due,
        "pending_target_count": pending,
        "failed_target_count": failed,
        "missed_or_expired_target_count": missed,
        "invalid_target_count": invalid,
        "recovery_required": bool(recovery),
        "latest_successful_observation_at": None if latest is None else latest["timing"]["collected_at"],
        "latest_successful_target": None if latest is None else latest["provider"].split(":")[-1],
        "targets": targets,
    }


def audit_collection_health(
    *,
    as_of: datetime,
    schedule_path: Path | str = game_day.SCHEDULE_PATH,
    moneyline_history_path: Path | str = MONEYLINE_HISTORY_PATH,
    moneyline_attempt_path: Path | str = MONEYLINE_ATTEMPT_PATH,
    totals_history_path: Path | str = TOTALS_HISTORY_PATH,
    totals_attempt_path: Path | str = TOTALS_ATTEMPT_PATH,
    game_id: str | None = None,
    hours: float = 48.0,
    include_all: bool = False,
) -> dict[str, Any]:
    """Derive collection coverage without fetching, writing, or recovering."""
    if as_of.tzinfo is None:
        raise CollectionHealthError("as_of must include a timezone")
    if hours < 0:
        raise CollectionHealthError("hours must be nonnegative")
    now = as_of.astimezone(UTC)
    try:
        schedule = game_day.load_schedule(schedule_path)
        moneyline_history = read_operational_history(moneyline_history_path)
        moneyline_attempts = read_collection_attempts(moneyline_attempt_path)
        moneyline = _lane_evidence(
            tuple(
                row
                for row in moneyline_history
                if _timestamp(row["timing"]["collected_at"], "collected_at") <= now
            ),
            tuple(
                row
                for row in moneyline_attempts
                if _timestamp(row["attempted_at"], "attempted_at") <= now
            ),
            prefix=MONEYLINE_PROVIDER_PREFIX,
            totals=False,
        )
        totals_history = read_totals_history(totals_history_path)
        totals_attempts = read_totals_attempts(totals_attempt_path)
        totals = _lane_evidence(
            tuple(
                row
                for row in totals_history
                if _timestamp(row["timing"]["collected_at"], "collected_at") <= now
            ),
            tuple(
                row
                for row in totals_attempts
                if _timestamp(row["attempted_at"], "attempted_at") <= now
            ),
            prefix=TOTALS_PROVIDER_PREFIX,
            totals=True,
        )
        _validate_canonical_evidence(schedule, moneyline, totals)
    except (game_day.GameDayInputError, OperationalHistoryError, CollectionAttemptError, OperationalTotalsError, TotalsAttemptError, OSError) as exc:
        raise CollectionHealthError(str(exc)) from exc
    if game_id is not None:
        try:
            games = (game_day.resolve_game(game_id, schedule),)
        except game_day.GameDayInputError as exc:
            raise CollectionHealthError(str(exc)) from exc
    else:
        games = tuple(
            game for game in schedule
            if -360.0 <= (_timestamp(game["kickoff_at"], "kickoff_at") - now).total_seconds() / 60.0 <= hours * 60.0
        )
    reports = []
    for game in games:
        kickoff = _timestamp(game["kickoff_at"], "kickoff_at")
        minutes = (kickoff - now).total_seconds() / 60.0
        report = {
            "game_id": game["game_id"],
            "away_team": game["away_team"],
            "home_team": game["home_team"],
            "kickoff_at": kickoff.isoformat().replace("+00:00", "Z"),
            "as_of": now.isoformat().replace("+00:00", "Z"),
            "minutes_to_kickoff": minutes,
            "moneyline": _lane_report(str(game["game_id"]), minutes, moneyline),
            "totals": _lane_report(str(game["game_id"]), minutes, totals),
        }
        actionable = any(report[lane]["overall"] in {"ACTION_NEEDED", "DEGRADED", "INVALID"} for lane in ("moneyline", "totals"))
        if game_id is not None or include_all or actionable:
            reports.append(report)
    return {"classification": CLASSIFICATION, "read_only": True, "non_prospective": True, "odds_fetch": False, "as_of": now.isoformat().replace("+00:00", "Z"), "games": reports}


def _print_report(report: Mapping[str, Any]) -> None:
    print("GRIDIRON COLLECTION HEALTH")
    print("READ-ONLY | NON-PROSPECTIVE | NO ODDS FETCH")
    if not report["games"]:
        print("No games require attention in the selected interval.")
        return
    for game in report["games"]:
        print(f"\nGAME: {game['game_id']}  {game['away_team']} @ {game['home_team']}")
        print(f"KICKOFF: {game['kickoff_at']}  AS OF: {game['as_of']}")
        print(f"MONEYLINE: {game['moneyline']['overall']}  TOTALS: {game['totals']['overall']}")
        print(f"{'TARGET':<16}{'MONEYLINE':<29}TOTALS")
        for target in TARGET_ORDER:
            moneyline = game["moneyline"]["targets"][target]
            totals = game["totals"]["targets"][target]
            print(f"{target:<16}{moneyline['state']:<29}{totals['state']}")
            for lane, item in (("moneyline", moneyline), ("totals", totals)):
                if item["state"] not in {"SUCCESS", "NOT_YET_DUE"}:
                    print(f"  {lane}: {item['reason']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--game")
    scope.add_argument("--upcoming", action="store_true")
    parser.add_argument("--hours", type=float, default=48.0)
    parser.add_argument("--as-of")
    parser.add_argument("--all", action="store_true", dest="include_all")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--schedule", type=Path, default=game_day.SCHEDULE_PATH)
    parser.add_argument("--moneyline-history", type=Path, default=MONEYLINE_HISTORY_PATH)
    parser.add_argument("--moneyline-attempts", type=Path, default=MONEYLINE_ATTEMPT_PATH)
    parser.add_argument("--totals-history", type=Path, default=TOTALS_HISTORY_PATH)
    parser.add_argument("--totals-attempts", type=Path, default=TOTALS_ATTEMPT_PATH)
    args = parser.parse_args(argv)
    try:
        as_of = datetime.now(UTC) if args.as_of is None else _timestamp(args.as_of, "as_of")
        report = audit_collection_health(
            as_of=as_of, schedule_path=args.schedule,
            moneyline_history_path=args.moneyline_history,
            moneyline_attempt_path=args.moneyline_attempts,
            totals_history_path=args.totals_history,
            totals_attempt_path=args.totals_attempts,
            game_id=args.game, hours=args.hours, include_all=args.include_all,
        )
    except CollectionHealthError as exc:
        print(f"COLLECTION HEALTH: INVALID — {exc}", file=sys.stderr)
        return 2
    if args.json_output:
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    else:
        _print_report(report)
    actionable = any(
        game[lane]["overall"] in {"ACTION_NEEDED", "DEGRADED", "INVALID"}
        for game in report["games"] for lane in ("moneyline", "totals")
    )
    return 1 if actionable else 0


if __name__ == "__main__":
    raise SystemExit(main())
