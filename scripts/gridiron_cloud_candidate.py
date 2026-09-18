"""Private NON_PROSPECTIVE_CLOUD_CANDIDATE collection entrypoint."""

from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from gridiron.market.cloud_evidence import (
    CLASSIFICATION,
    CloudEvidenceError,
    FirestoreEvidenceRepository,
    LeaseToken,
    LeaseUnavailableError,
    build_raw_response,
    build_slot,
)
from gridiron.market.collection_attempts import build_collection_attempt
from gridiron.market.operational_history import (
    build_operational_history_record,
)
from gridiron.market.operational_totals import (
    AUTOMATIC_PROVIDER_PREFIX as TOTALS_PROVIDER_PREFIX,
)
from gridiron.market.operational_totals import (
    TARGET_WINDOWS,
    build_totals_observation,
    parse_timestamp,
)
from gridiron.market.totals_collection_attempts import (
    build_totals_attempt,
)
from scripts import gridiron_game_day as game_day
from scripts import gridiron_market_collector as moneyline
from scripts import gridiron_totals_collector as totals

LEASE_TTL = timedelta(minutes=10)
REQUESTED_BOOKS = ("betmgm", "draftkings", "fanduel")


def _moneyline_attempt(
    game: dict[str, object], target: moneyline.CollectionWindow, now: datetime,
    *, result: str, reason: str, observation_id: str | None = None,
) -> dict[str, Any]:
    return build_collection_attempt(
        game_id=str(game["game_id"]),
        collection_target=target.label,
        target_minutes_to_kickoff=target.target_minutes,
        kickoff_at=str(game["kickoff_at"]),
        attempted_at=now,
        result=result,
        reason_code=reason,
        observation_id=observation_id,
    )


def _slot_for_moneyline(
    game: dict[str, object], target: moneyline.CollectionWindow
) -> dict[str, Any]:
    return build_slot(
        game_id=str(game["game_id"]),
        market_type="MONEYLINE",
        target_label=target.label,
        kickoff_at=str(game["kickoff_at"]),
        target_minutes=target.target_minutes,
        lower_bound_minutes=target.minimum_minutes,
        upper_bound_minutes=target.maximum_minutes,
    )


def _slot_for_totals(game: dict[str, object], target: str) -> dict[str, Any]:
    center, lower, upper = TARGET_WINDOWS[target]
    return build_slot(
        game_id=str(game["game_id"]),
        market_type="TOTALS",
        target_label=target,
        kickoff_at=str(game["kickoff_at"]),
        target_minutes=center,
        lower_bound_minutes=lower,
        upper_bound_minutes=upper,
    )


def _lease(repository: Any, slot: dict[str, Any], owner: str, now: datetime) -> LeaseToken | None:
    try:
        return repository.acquire_lease(slot, owner=owner, now=now, ttl=LEASE_TTL)
    except LeaseUnavailableError:
        return None


def _prepare_lane_slots(
    repository: Any,
    schedule: tuple[dict[str, object], ...],
    *,
    now: datetime,
    owner: str,
    lane: str,
    counters: dict[str, int],
) -> list[tuple[dict[str, object], str, LeaseToken]]:
    eligible: list[tuple[dict[str, object], str, LeaseToken]] = []
    for game in schedule:
        kickoff = parse_timestamp(game["kickoff_at"], "kickoff_at")
        minutes = (kickoff - now).total_seconds() / 60.0
        if minutes <= 0:
            counters["post_kickoff"] += 1
            continue
        if minutes > max(window[2] for window in TARGET_WINDOWS.values()):
            continue
        if lane == "MONEYLINE":
            targets = [
                (window.label, window.minimum_minutes, _slot_for_moneyline(game, window), window)
                for window in moneyline.WINDOWS
            ]
            current = moneyline.eligible_window(minutes)
            current_label = None if current is None else current.label
        else:
            targets = [
                (target, bounds[1], _slot_for_totals(game, target), target)
                for target, bounds in TARGET_WINDOWS.items()
            ]
            current_label = totals.eligible_target(minutes)
        for label, lower, slot, target_object in targets:
            existing = repository.inspect_slot(slot["slot_id"])
            if existing is not None and str(existing.get("state", "")).startswith("TERMINAL_"):
                counters["existing"] += 1
                continue
            if existing is not None and existing.get("state") == "RAW_CAPTURED":
                token = _lease(repository, slot, owner, now)
                if token is None:
                    counters["contended"] += 1
                else:
                    eligible.append((game, label, token))
                continue
            if minutes < lower:
                token = _lease(repository, slot, owner, now)
                if token is None:
                    counters["contended"] += 1
                    continue
                if lane == "MONEYLINE":
                    attempt = _moneyline_attempt(
                        game, target_object, now,
                        result="SKIPPED_OUTSIDE_WINDOW", reason="MISSED_WINDOW",
                    )
                else:
                    attempt = build_totals_attempt(
                        game_id=str(game["game_id"]), target_label=label,
                        kickoff_at=str(game["kickoff_at"]), attempted_at=now,
                        result="MISSED_WINDOW", reason_code="MISSED_WINDOW",
                    )
                repository.commit_terminal_attempt(token, attempt=attempt)
                counters["missed"] += 1
            elif current_label == label:
                token = _lease(repository, slot, owner, now)
                if token is None:
                    counters["contended"] += 1
                    continue
                eligible.append((game, label, token))
    return eligible


def _collect_moneyline(
    repository: Any,
    slots: list[tuple[dict[str, object], str, LeaseToken]],
    *,
    now: datetime,
    counters: dict[str, int],
) -> None:
    prepared: list[tuple[dict[str, object], str, LeaseToken, float]] = []
    for game, target, token in slots:
        try:
            def_epa = game_day.automatic_def_epa_for_game(game)
            prepared.append((game, target, token, def_epa))
        except game_day.GameDayInputError as exc:
            window = next(item for item in moneyline.WINDOWS if item.label == target)
            attempt = _moneyline_attempt(
                game, window, now, result="FAILED", reason=moneyline._reason_code(exc)
            )
            repository.commit_terminal_attempt(token, attempt=attempt)
            counters["failed"] += 1
    def derive(
        game: dict[str, object], target: str, token: LeaseToken, def_epa: float,
        payload: object, raw_response_id: str,
    ) -> None:
        window = next(item for item in moneyline.WINDOWS if item.label == target)
        try:
            prices, observed_at = game_day.parse_live_prices(payload, game)
            snapshot = game_day.build_game_day_snapshot(
                game, prices, captured_at=now, observed_at=observed_at,
                provider=moneyline.AUTOMATIC_PROVIDER_PREFIX + target,
            )
            source = "frozen Week 1 neutral rule" if int(game["week"]) == 1 else "automatic nflverse frozen feature"
            prediction = game_day.build_operational_prediction(
                snapshot, def_epa=def_epa, def_epa_source=source
            )
            observation = build_operational_history_record(prediction)
            attempt = _moneyline_attempt(
                game, window, now, result="SUCCESS", reason="SUCCESS",
                observation_id=observation["observation_id"],
            )
            repository.commit_success(
                token, raw_response_id=raw_response_id,
                observation=observation, attempt=attempt,
            )
            counters["success"] += 1
        except (ValueError, KeyError, TypeError) as exc:
            attempt = _moneyline_attempt(
                game, window, now, result="FAILED", reason=moneyline._reason_code(exc)
            )
            repository.commit_terminal_attempt(token, attempt=attempt)
            counters["failed"] += 1

    fresh: list[tuple[dict[str, object], str, LeaseToken, float]] = []
    for game, target, token, def_epa in prepared:
        state = repository.inspect_slot(token.slot_id)
        raw_id = None if state is None else state.get("raw_response_id")
        if state is not None and state.get("state") == "RAW_CAPTURED" and raw_id:
            retained = repository.get_raw_response(str(raw_id))
            derive(game, target, token, def_epa, retained["payload"], str(raw_id))
        else:
            fresh.append((game, target, token, def_epa))
    if not fresh:
        return
    try:
        payload = game_day.fetch_live_moneyline_payload()
    except game_day.GameDayInputError as exc:
        for game, target, token, _ in fresh:
            window = next(item for item in moneyline.WINDOWS if item.label == target)
            repository.commit_terminal_attempt(
                token,
                attempt=_moneyline_attempt(
                    game, window, now, result="FAILED", reason=moneyline._reason_code(exc)
                ),
            )
            counters["failed"] += 1
        return
    raw = build_raw_response(
        provider="the-odds-api", lane="MONEYLINE", product="h2h-us-three-book",
        requested_books=REQUESTED_BOOKS, fetched_at=datetime.now(UTC), payload=payload,
        slot_ids=(token.slot_id for _, _, token, _ in fresh), parser_version="step91q-v1",
    )
    repository.checkpoint_raw((token for _, _, token, _ in fresh), raw)
    counters["provider_calls"] += 1
    for game, target, token, def_epa in fresh:
        derive(
            game, target, token, def_epa, payload, str(raw["raw_response_id"])
        )


def _collect_totals(
    repository: Any,
    slots: list[tuple[dict[str, object], str, LeaseToken]],
    *, now: datetime, counters: dict[str, int],
) -> None:
    def derive(
        game: dict[str, object], target: str, token: LeaseToken,
        payload: object, raw_response_id: str,
    ) -> None:
        try:
            books = totals.parse_live_totals(payload, game, now)
            observation = build_totals_observation(
                game, books, collected_at=now, target_label=target,
                provider=TOTALS_PROVIDER_PREFIX + target,
            )
            attempt = build_totals_attempt(
                game_id=str(game["game_id"]), target_label=target,
                kickoff_at=str(game["kickoff_at"]), attempted_at=now,
                result="SUCCESS", reason_code="SUCCESS",
                observation_id=observation["observation_id"],
            )
            repository.commit_success(
                token, raw_response_id=raw_response_id,
                observation=observation, attempt=attempt,
            )
            counters["success"] += 1
        except (ValueError, KeyError, TypeError) as exc:
            repository.commit_terminal_attempt(
                token,
                attempt=build_totals_attempt(
                    game_id=str(game["game_id"]), target_label=target,
                    kickoff_at=str(game["kickoff_at"]), attempted_at=now,
                    result="FAILED", reason_code=totals._reason(exc),
                ),
            )
            counters["failed"] += 1

    fresh: list[tuple[dict[str, object], str, LeaseToken]] = []
    for game, target, token in slots:
        state = repository.inspect_slot(token.slot_id)
        raw_id = None if state is None else state.get("raw_response_id")
        if state is not None and state.get("state") == "RAW_CAPTURED" and raw_id:
            retained = repository.get_raw_response(str(raw_id))
            derive(game, target, token, retained["payload"], str(raw_id))
        else:
            fresh.append((game, target, token))
    if not fresh:
        return
    try:
        payload = totals.fetch_live_totals_payload()
    except ValueError as exc:
        for game, target, token in fresh:
            repository.commit_terminal_attempt(
                token,
                attempt=build_totals_attempt(
                    game_id=str(game["game_id"]), target_label=target,
                    kickoff_at=str(game["kickoff_at"]), attempted_at=now,
                    result="FAILED", reason_code=totals._reason(exc),
                ),
            )
            counters["failed"] += 1
        return
    fetched_at = datetime.now(UTC)
    raw = build_raw_response(
        provider="the-odds-api", lane="TOTALS", product="totals-us-three-book",
        requested_books=REQUESTED_BOOKS, fetched_at=fetched_at, payload=payload,
        slot_ids=(token.slot_id for _, _, token in fresh), parser_version="step91r-v1",
    )
    repository.checkpoint_raw((token for _, _, token in fresh), raw)
    counters["provider_calls"] += 1
    for game, target, token in fresh:
        derive(game, target, token, payload, str(raw["raw_response_id"]))


def run_cloud_candidate(
    repository: Any, *, now: datetime, owner: str,
    schedule_path: Path | str = game_day.SCHEDULE_PATH,
) -> dict[str, Any]:
    """Run both candidate lanes without changing local operational evidence."""
    if now.tzinfo is None:
        raise CloudEvidenceError("cloud invocation time must include a timezone")
    if not os.environ.get("GRIDIRON_ODDS_API_KEY"):
        raise CloudEvidenceError("GRIDIRON_ODDS_API_KEY is not set")
    now = now.astimezone(UTC)
    schedule = game_day.load_schedule(schedule_path)
    counters = {
        "success": 0, "failed": 0, "missed": 0, "post_kickoff": 0,
        "existing": 0, "contended": 0, "provider_calls": 0,
    }
    moneyline_slots = _prepare_lane_slots(
        repository, schedule, now=now, owner=owner, lane="MONEYLINE", counters=counters
    )
    totals_slots = _prepare_lane_slots(
        repository, schedule, now=now, owner=owner, lane="TOTALS", counters=counters
    )
    _collect_moneyline(repository, moneyline_slots, now=now, counters=counters)
    _collect_totals(repository, totals_slots, now=now, counters=counters)
    return {
        "classification": CLASSIFICATION,
        "authority": "CANDIDATE_SHADOW_ONLY",
        "invoked_at": now.isoformat().replace("+00:00", "Z"),
        **counters,
    }


def collect_candidate(_request: object) -> tuple[dict[str, Any], int]:
    """Functions Framework entrypoint for a private authenticated Cloud Run service."""
    try:
        repository = FirestoreEvidenceRepository.from_default_client()
        result = run_cloud_candidate(
            repository, now=datetime.now(UTC), owner=f"cloud-run-{uuid.uuid4().hex}"
        )
        return result, 200
    except Exception as exc:  # noqa: BLE001 - boundary must fail closed without leakage.
        return {
            "classification": CLASSIFICATION,
            "authority": "CANDIDATE_SHADOW_ONLY",
            "status": "FAILED_CLOSED",
            "error_type": type(exc).__name__,
        }, 500
