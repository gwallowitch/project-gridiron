"""Prospective evidence-process integrity controls for Step 91H."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from gridiron.market.prospective_audit import canonical_json
from gridiron.market.prospective_ledger import CANDIDATE_ID, validate_ledger
from gridiron.market.prospective_market_ingestion import (
    ProspectiveMarketIngestionError,
    load_market_snapshot,
    preview_market_decision,
)

CAPTURE_MINUTES = (55, 65)
MAX_QUOTE_AGE = timedelta(minutes=10)
SETTLEMENT_DEADLINE = timedelta(hours=48)
TERMINAL_CAPTURE = {"accepted", "rejected", "unavailable", "cancelled", "excluded"}
REASON_CODES = {
    "NO_VALID_CONSENSUS",
    "NO_EXECUTABLE_DRAFTKINGS_PRICE",
    "STALE_INPUT",
    "MALFORMED_INPUT",
    "LATE_CAPTURE",
    "DEF_EPA_UNAVAILABLE",
    "MARKET_UNAVAILABLE",
    "GAME_CANCELLED",
    "GAME_POSTPONED",
    "DUPLICATE_GAME",
    "OTHER_FROZEN_EXCLUSION",
}


class ProspectiveIntegrityError(ValueError):
    """Raised when a Step 91H integrity invariant is violated."""


def _utc(value: str, field: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        result = datetime.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise ProspectiveIntegrityError(f"{field} must be timezone-aware ISO-8601") from exc
    if result.tzinfo is None:
        raise ProspectiveIntegrityError(f"{field} must be timezone-aware ISO-8601")
    return result.astimezone(UTC)


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def canonical_game_id(season: int, week: int, away_team: str, home_team: str) -> str:
    if season != 2026 or not 1 <= week <= 16:
        raise ProspectiveIntegrityError("game must be 2026 REG Week 1-16")
    if not away_team or not home_team or away_team == home_team:
        raise ProspectiveIntegrityError("canonical game teams must be distinct")
    return f"{season}_{week:02d}_{away_team}_{home_team}"


def raw_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _event_hash(event: dict[str, Any], previous_hash: str) -> str:
    material = canonical_json(event).encode() + previous_hash.encode()
    return hashlib.sha256(material).hexdigest()


def read_chain(path: Path | str) -> tuple[dict[str, Any], ...]:
    chain_path = Path(path)
    if not chain_path.exists():
        return ()
    events = []
    for number, line in enumerate(chain_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProspectiveIntegrityError(f"invalid chain JSON at line {number}") from exc
        events.append(event)
    validate_chain(events)
    return tuple(events)


def validate_chain(events: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> str:
    previous = "0" * 64
    for index, stored in enumerate(events):
        event = dict(stored)
        event_hash = event.pop("event_hash", None)
        if event.get("previous_hash") != previous:
            raise ProspectiveIntegrityError(f"broken previous hash at event {index}")
        expected = _event_hash(event, previous)
        if event_hash != expected:
            raise ProspectiveIntegrityError(f"invalid event hash at event {index}")
        previous = expected
    return previous


def append_chain_event(path: Path | str, payload: dict[str, Any]) -> dict[str, Any]:
    chain_path = Path(path)
    existing = read_chain(chain_path)
    previous = existing[-1]["event_hash"] if existing else "0" * 64
    event = dict(payload)
    event["previous_hash"] = previous
    event["event_hash"] = _event_hash(event, previous)
    validate_chain([*existing, event])
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    with chain_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical_json(event) + "\n")
    return event


def export_anchor(path: Path | str) -> dict[str, Any]:
    events = read_chain(path)
    return {
        "events": len(events),
        "terminal_hash": validate_chain(list(events)),
        "external_publication": None,
        "limitation": "offline digest does not prevent deletion of the entire ledger",
    }


def register_scheduled_game(
    chain_path: Path | str,
    *,
    season: int,
    week: int,
    away_team: str,
    home_team: str,
    kickoff_at: str,
    provider_ids: list[str] | None = None,
) -> dict[str, Any]:
    game_id = canonical_game_id(season, week, away_team, home_team)
    existing = read_chain(chain_path)
    if any(event.get("game_id") == game_id and event["event_type"] == "SCHEDULED" for event in existing):
        raise ProspectiveIntegrityError("duplicate canonical game identity")
    aliases = sorted(set(provider_ids or []))
    prior_aliases = {alias for event in existing for alias in event.get("provider_ids", [])}
    if prior_aliases.intersection(aliases):
        raise ProspectiveIntegrityError("alternate provider ID already maps to another game")
    return append_chain_event(
        chain_path,
        {
            "event_type": "SCHEDULED",
            "game_id": game_id,
            "season": 2026,
            "season_type": "REG",
            "week": week,
            "away_team": away_team,
            "home_team": home_team,
            "kickoff_at": _utc_text(_utc(kickoff_at, "kickoff_at")),
            "kickoff_source": "retained NFL official schedule artifact",
            "provider_ids": aliases,
            "status": "scheduled",
        },
    )


def capture_window_status(receipt: datetime, kickoff: datetime) -> str:
    minutes = (kickoff - receipt).total_seconds() / 60
    return "IN_WINDOW" if CAPTURE_MINUTES[0] <= minutes <= CAPTURE_MINUTES[1] else "OUTSIDE_WINDOW"


def record_capture_attempt(
    chain_path: Path | str,
    raw_path: Path | str,
    artifact_dir: Path | str,
    *,
    receipt_at: datetime | None = None,
    reason_code: str | None = None,
) -> dict[str, Any]:
    receipt = (receipt_at or datetime.now(UTC)).astimezone(UTC)
    data = Path(raw_path).read_bytes()
    digest = raw_sha256(data)
    retained = Path(artifact_dir) / f"{digest}.json"
    retained.parent.mkdir(parents=True, exist_ok=True)
    if not retained.exists():
        retained.write_bytes(data)
    try:
        raw = load_market_snapshot(raw_path)
        game = raw["game"]
        game_id = canonical_game_id(game["season"], game["week"], game["away_team"], game["home_team"])
        kickoff = _utc(game["kickoff_at"], "kickoff_at")
        if capture_window_status(receipt, kickoff) != "IN_WINDOW":
            raise ProspectiveIntegrityError("capture receipt is outside the frozen window")
        observed = [_utc(item["observed_at"], "observed_at") for item in raw["offers"]]
        if any(value > receipt for value in observed):
            raise ProspectiveIntegrityError("provider observation postdates receipt")
        if any(receipt - value > MAX_QUOTE_AGE for value in observed):
            raise ProspectiveIntegrityError("market quote is stale")
        raw_for_decision = dict(raw)
        raw_for_decision["captured_at"] = _utc_text(receipt)
        decision = preview_market_decision(raw_for_decision)
        status = "accepted"
        code = None
    except (ProspectiveMarketIngestionError, ProspectiveIntegrityError, KeyError) as exc:
        decision = None
        status = "rejected"
        message = str(exc).lower()
        code = reason_code or (
            "STALE_INPUT" if "stale" in message else "LATE_CAPTURE" if "window" in message else "MALFORMED_INPUT"
        )
        if code not in REASON_CODES:
            raise ProspectiveIntegrityError("invalid deterministic reason code") from exc
    return append_chain_event(
        chain_path,
        {
            "event_type": "CAPTURE_ATTEMPT",
            "game_id": locals().get("game_id"),
            "receipt_at": _utc_text(receipt),
            "raw_sha256": digest,
            "raw_artifact": str(retained),
            "status": status,
            "reason_code": code,
            "provider_observed_at": sorted(item.get("observed_at") for item in raw.get("offers", [])) if "raw" in locals() else [],
            "decision_event_id": decision["event_id"] if decision else None,
            "def_epa_provenance": {
                "source_id": "project-gridiron-def-epa-trend",
                "calculation_version": "frozen-input-v1",
                "as_of": _utc_text(receipt),
                "correction_policy": "append separately; never rewrite",
            },
        },
    )


def record_status(chain_path: Path | str, *, game_id: str, status: str, reason_code: str, recorded_at: str) -> dict[str, Any]:
    if status not in {"unavailable", "cancelled", "postponed", "excluded", "capture_attempted"}:
        raise ProspectiveIntegrityError("invalid manifest status")
    if reason_code not in REASON_CODES:
        raise ProspectiveIntegrityError("invalid deterministic reason code")
    return append_chain_event(chain_path, {"event_type": "STATUS", "game_id": game_id, "status": status, "reason_code": reason_code, "recorded_at": _utc_text(_utc(recorded_at, "recorded_at"))})


def edge_trim_order(decisions: list[dict[str, Any]], fraction: float) -> list[dict[str, Any]]:
    population = [item for item in decisions if item["is_bet"] and item.get("result") in {"HOME", "AWAY"}]
    ordered = sorted(population, key=lambda item: (-item["edge"], item["observation_id"]))
    return ordered[math.floor(len(ordered) * fraction) :]


def market_side(home_probability: float) -> str:
    if 0.45 <= home_probability <= 0.55:
        return "BALANCED"
    return "FAVORITE" if home_probability > 0.55 else "UNDERDOG"


def probability_metric_population(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in decisions if item.get("result") in {"HOME", "AWAY"}]


def audit_manifest(chain_path: Path | str, ledger_path: Path | str, *, as_of: str) -> dict[str, Any]:
    events = read_chain(chain_path)
    state = validate_ledger(ledger_path)
    scheduled = {event["game_id"]: event for event in events if event["event_type"] == "SCHEDULED"}
    latest_status = {game_id: "scheduled" for game_id in scheduled}
    for event in events:
        if event.get("game_id") in latest_status and event.get("status"):
            latest_status[event["game_id"]] = event["status"]
    omissions = sorted(game_id for game_id, status in latest_status.items() if status == "scheduled")
    now = _utc(as_of, "as_of")
    overdue = []
    for event in events:
        if event["event_type"] == "GAME_FINAL" and now > _utc(event["final_at"], "final_at") + SETTLEMENT_DEADLINE:
            game_id = event["game_id"]
            decision = state.decisions.get(game_id)
            if decision and decision["is_bet"] and game_id not in state.settlements:
                overdue.append(game_id)
    return {
        "chain_valid": True,
        "terminal_hash": validate_chain(list(events)),
        "scheduled_games": len(scheduled),
        "unaccounted_games": omissions,
        "overdue_settlements": sorted(overdue),
        "decisions": len(state.decisions),
        "settlements": len(state.settlements),
        "complete_season": bool(scheduled) and not omissions and not overdue and all(status != "postponed" for status in latest_status.values()),
        "candidate_id": CANDIDATE_ID,
        "prospective_evidence_count": len(state.decisions),
    }


__all__ = ["ProspectiveIntegrityError", "append_chain_event", "audit_manifest", "canonical_game_id", "capture_window_status", "edge_trim_order", "export_anchor", "market_side", "probability_metric_population", "raw_sha256", "read_chain", "record_capture_attempt", "record_status", "register_scheduled_game", "validate_chain"]
