"""Deterministic game-day operations for Step 91I prospective collection."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from gridiron.market.prospective_audit import canonical_json
from gridiron.market.prospective_integrity import (
    ProspectiveIntegrityError,
    append_chain_event,
    audit_manifest,
    canonical_game_id,
    raw_sha256,
    read_chain,
    record_capture_attempt,
    record_status,
    register_scheduled_game,
)
from gridiron.market.prospective_ledger import (
    CANDIDATE_ID,
    CONSENSUS_BOOKS,
    DEF_EPA_COEFFICIENT,
    EXECUTION_BOOK,
    INTERCEPT,
    MARKET_COEFFICIENT,
    PROTOCOL_ID,
    RESIDUAL_CAP,
    LedgerError,
    capture_decision,
    ledger_summary,
    settle_decision,
    validate_ledger,
)
from gridiron.market.prospective_market_ingestion import (
    ProspectiveMarketIngestionError,
    build_ledger_payload,
    load_market_snapshot,
)

OPERATIONS_ID = "step91i-prospective-collection-operations-v1"
REAL_EVIDENCE = "REAL_PROSPECTIVE_EVIDENCE"
DRY_RUN_EVIDENCE = "SYNTHETIC_TEST_DATA"
FROZEN_PROTOCOL = {
    "candidate_id": "market-plus-def-epa-capped-0425-v1",
    "protocol_id": "step91b-prospective-validation-v1",
    "market_coefficient": 4.980172,
    "def_epa_coefficient": 1.044827,
    "intercept": -2.514766,
    "residual_cap": 0.0425,
    "market_books": [
        "Bet365",
        "SI",
        "Betway",
        "BetMGM",
        "FanDuel",
        "Caesars",
        "DraftKings",
    ],
    "execution_book": "DraftKings",
    "eligibility": "strictly_positive_edge",
    "population": {"season": 2026, "season_type": "REG", "weeks": [1, 16]},
    "week_1_missing_def_epa": 0.0,
    "later_missing_def_epa": "reject",
}


class ProspectiveOperationsError(ValueError):
    """Raised when a Step 91I operational invariant is violated."""


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ProspectiveOperationsError(
            f"{field} must be an explicit ISO-8601 timestamp"
        )
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ProspectiveOperationsError(
            f"{field} must be an explicit ISO-8601 timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise ProspectiveOperationsError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _load_json(path: Path | str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProspectiveOperationsError(f"cannot load JSON input: {exc}") from exc


def assert_frozen_protocol(candidate: Mapping[str, Any] | None = None) -> None:
    """Fail loudly if runtime constants or a supplied declaration differ."""
    runtime = {
        **FROZEN_PROTOCOL,
        "candidate_id": CANDIDATE_ID,
        "protocol_id": PROTOCOL_ID,
        "market_coefficient": MARKET_COEFFICIENT,
        "def_epa_coefficient": DEF_EPA_COEFFICIENT,
        "intercept": INTERCEPT,
        "residual_cap": RESIDUAL_CAP,
        "market_books": list(CONSENSUS_BOOKS),
        "execution_book": EXECUTION_BOOK,
    }
    if runtime != FROZEN_PROTOCOL:
        raise ProspectiveOperationsError("runtime frozen protocol mismatch")
    if candidate is not None and dict(candidate) != FROZEN_PROTOCOL:
        raise ProspectiveOperationsError("declared frozen protocol mismatch")


def initialize_manifest(
    schedule_path: Path | str, manifest_path: Path | str
) -> dict[str, Any]:
    """Idempotently register every game from a retained canonical schedule."""
    assert_frozen_protocol()
    schedule = _load_json(schedule_path)
    if not isinstance(schedule, list):
        raise ProspectiveOperationsError("schedule must be a JSON list")
    existing = read_chain(manifest_path)
    scheduled = {
        e["game_id"]: e for e in existing if e.get("event_type") == "SCHEDULED"
    }
    added = 0
    seen: set[str] = set()
    provider_ids: set[str] = set()
    for game in schedule:
        if not isinstance(game, dict):
            raise ProspectiveOperationsError("each scheduled game must be an object")
        try:
            game_id = canonical_game_id(
                game["season"], game["week"], game["away_team"], game["home_team"]
            )
            kickoff_at = _utc_text(_utc(game["kickoff_at"], "kickoff_at"))
            aliases = sorted(set(game.get("provider_ids", [])))
        except (KeyError, TypeError, ProspectiveIntegrityError) as exc:
            raise ProspectiveOperationsError(f"invalid scheduled game: {exc}") from exc
        if game.get("season_type") != "REG" or game.get("game_id", game_id) != game_id:
            raise ProspectiveOperationsError(
                "schedule violates canonical 2026 REG identity"
            )
        if game_id in seen:
            raise ProspectiveOperationsError(f"duplicate scheduled game: {game_id}")
        if any(not isinstance(alias, str) or not alias for alias in aliases):
            raise ProspectiveOperationsError("provider IDs must be non-empty strings")
        if provider_ids.intersection(aliases):
            raise ProspectiveOperationsError("duplicate provider ID in schedule")
        seen.add(game_id)
        provider_ids.update(aliases)
        prior = scheduled.get(game_id)
        if prior:
            comparable = {
                "kickoff_at": kickoff_at,
                "away_team": game["away_team"],
                "home_team": game["home_team"],
                "week": game["week"],
                "provider_ids": aliases,
            }
            if any(prior.get(key) != value for key, value in comparable.items()):
                raise ProspectiveOperationsError(
                    f"existing manifest conflicts for {game_id}"
                )
            continue
        register_scheduled_game(
            manifest_path,
            season=game["season"],
            week=game["week"],
            away_team=game["away_team"],
            home_team=game["home_team"],
            kickoff_at=kickoff_at,
            provider_ids=aliases,
        )
        added += 1
    return {"classification": REAL_EVIDENCE, "expected": len(seen), "added": added}


def _scheduled_event(
    events: tuple[dict[str, Any], ...], game_id: str
) -> dict[str, Any]:
    matches = [
        e
        for e in events
        if e.get("event_type") == "SCHEDULED" and e.get("game_id") == game_id
    ]
    if len(matches) != 1:
        raise ProspectiveOperationsError(
            "explicit game identity is not scheduled exactly once"
        )
    return matches[0]


def capture_game(
    manifest_path: Path | str,
    ledger_path: Path | str,
    raw_path: Path | str,
    artifact_dir: Path | str,
    *,
    game_id: str,
    receipt_at: str,
) -> dict[str, Any]:
    """Capture one real game through Step 91H, Step 91D, then Step 91C."""
    assert_frozen_protocol()
    events = read_chain(manifest_path)
    scheduled = _scheduled_event(events, game_id)
    state = validate_ledger(ledger_path)
    if game_id in state.decisions:
        raise ProspectiveOperationsError(
            "already captured game; valid decisions are immutable"
        )
    accepted = [
        event
        for event in events
        if event.get("game_id") == game_id and event.get("status") == "accepted"
    ]
    receipt = _utc(receipt_at, "receipt_at")
    if receipt >= _utc(scheduled["kickoff_at"], "kickoff_at"):
        raise ProspectiveOperationsError("capture must be pre-kickoff")
    raw = load_market_snapshot(raw_path)
    raw_game = raw.get("game", {})
    expected = canonical_game_id(
        raw_game.get("season"),
        raw_game.get("week"),
        raw_game.get("away_team"),
        raw_game.get("home_team"),
    )
    if raw_game.get("game_id") != game_id or expected != game_id:
        raise ProspectiveOperationsError(
            "raw snapshot does not match explicit canonical game identity"
        )
    normalized = dict(raw)
    normalized["captured_at"] = _utc_text(receipt)
    if accepted:
        prior = accepted[-1]
        if prior["receipt_at"] != normalized["captured_at"]:
            raise ProspectiveOperationsError(
                "accepted capture receipt cannot be changed"
            )
        retained = Path(prior["raw_artifact"])
        if (
            not retained.exists()
            or retained.read_bytes() != Path(raw_path).read_bytes()
        ):
            raise ProspectiveOperationsError(
                "accepted capture raw artifact cannot be changed"
            )
        try:
            decision = capture_decision(ledger_path, build_ledger_payload(normalized))
            validate_ledger(ledger_path)
        except (LedgerError, ProspectiveMarketIngestionError) as exc:
            raise ProspectiveOperationsError(
                f"interrupted append recovery failed: {exc}"
            ) from exc
        if decision["event_id"] != prior["decision_event_id"]:
            raise ProspectiveOperationsError(
                "recovered decision identity does not match accepted capture"
            )
        return {
            "classification": REAL_EVIDENCE,
            "attempt": prior,
            "decision": decision,
            "recovered_interrupted_append": True,
        }
    offers = raw.get("offers")
    reason_code = None
    if isinstance(offers, list):
        books = [offer.get("book") for offer in offers if isinstance(offer, dict)]
        draftkings = next(
            (
                offer
                for offer in offers
                if isinstance(offer, dict) and offer.get("book") == EXECUTION_BOOK
            ),
            None,
        )
        if len(offers) != len(CONSENSUS_BOOKS) or set(books) != set(CONSENSUS_BOOKS):
            reason_code = "NO_VALID_CONSENSUS"
        elif any(
            not isinstance(offer, dict)
            or offer.get("home_odds") is None
            or offer.get("away_odds") is None
            for offer in offers
        ):
            reason_code = (
                "NO_EXECUTABLE_DRAFTKINGS_PRICE"
                if draftkings is not None
                and (
                    draftkings.get("home_odds") is None
                    or draftkings.get("away_odds") is None
                )
                else "NO_VALID_CONSENSUS"
            )
    if raw_game.get("week") != 1 and raw.get("def_epa") is None:
        reason_code = "DEF_EPA_UNAVAILABLE"
    attempt = record_capture_attempt(
        manifest_path,
        raw_path,
        artifact_dir,
        receipt_at=receipt,
        reason_code=reason_code,
    )
    if attempt["status"] != "accepted":
        return {"classification": REAL_EVIDENCE, "attempt": attempt, "decision": None}
    try:
        decision = capture_decision(ledger_path, build_ledger_payload(normalized))
        validate_ledger(ledger_path)
    except (LedgerError, ProspectiveMarketIngestionError) as exc:
        raise ProspectiveOperationsError(
            f"append-only ledger rejected capture: {exc}"
        ) from exc
    return {"classification": REAL_EVIDENCE, "attempt": attempt, "decision": decision}


def record_game_status(
    manifest_path: Path | str, *, game_id: str, status: str, recorded_at: str
) -> dict[str, Any]:
    """Record a deterministic terminal or postponement state."""
    _scheduled_event(read_chain(manifest_path), game_id)
    reasons = {
        "postponed": "GAME_POSTPONED",
        "cancelled": "GAME_CANCELLED",
        "unavailable": "MARKET_UNAVAILABLE",
    }
    if status not in reasons:
        raise ProspectiveOperationsError(
            "status must be postponed, cancelled, or unavailable"
        )
    return record_status(
        manifest_path,
        game_id=game_id,
        status=status,
        reason_code=reasons[status],
        recorded_at=recorded_at,
    )


def settle_game(
    manifest_path: Path | str,
    ledger_path: Path | str,
    *,
    game_id: str,
    result: str,
    final_at: str,
    settled_at: str,
    result_source: Path | str,
) -> dict[str, Any]:
    """Append one settlement and immediately validate both stores."""
    events = read_chain(manifest_path)
    _scheduled_event(events, game_id)
    state = validate_ledger(ledger_path)
    if game_id in state.settlements:
        raise ProspectiveOperationsError(f"duplicate settlement for {game_id}")
    final_time = _utc(final_at, "final_at")
    settled_time = _utc(settled_at, "settled_at")
    if final_time < _utc(_scheduled_event(events, game_id)["kickoff_at"], "kickoff_at"):
        raise ProspectiveOperationsError("official final cannot precede kickoff")
    if settled_time < final_time:
        raise ProspectiveOperationsError("settlement cannot precede official final")
    source_path = Path(result_source)
    try:
        source_digest = raw_sha256(source_path.read_bytes())
    except OSError as exc:
        raise ProspectiveOperationsError(
            f"official result source is not retained: {exc}"
        ) from exc
    final_payload = {
        "event_type": "GAME_FINAL",
        "game_id": game_id,
        "result": result,
        "final_at": _utc_text(final_time),
        "settlement_source": "retained NFL official final gamebook/result artifact",
        "source_path": str(source_path),
        "source_sha256": source_digest,
    }
    prior_finals = [
        event
        for event in events
        if event.get("event_type") == "GAME_FINAL" and event.get("game_id") == game_id
    ]
    if prior_finals:
        prior = prior_finals[-1]
        if any(prior.get(key) != value for key, value in final_payload.items()):
            raise ProspectiveOperationsError("official final event cannot be replaced")
    else:
        append_chain_event(manifest_path, final_payload)
    try:
        event = settle_decision(
            ledger_path, game_id=game_id, result=result, settled_at=settled_at
        )
        validate_ledger(ledger_path)
    except LedgerError as exc:
        raise ProspectiveOperationsError(str(exc)) from exc
    return event


def operational_summary(
    manifest_path: Path | str, ledger_path: Path | str, *, as_of: str
) -> dict[str, Any]:
    """Return deterministic operational counts without changing populations."""
    events = read_chain(manifest_path)
    state = validate_ledger(ledger_path)
    scheduled = {e["game_id"] for e in events if e.get("event_type") == "SCHEDULED"}
    attempts = [e for e in events if e.get("event_type") == "CAPTURE_ATTEMPT"]
    latest: dict[str, str] = {game_id: "pending" for game_id in scheduled}
    for event in events:
        if event.get("game_id") in latest and event.get("status"):
            latest[event["game_id"]] = event["status"]
    audit = audit_manifest(manifest_path, ledger_path, as_of=as_of)
    ledger = ledger_summary(ledger_path)
    accounted_states = {"accepted", "rejected", "unavailable", "cancelled", "excluded"}
    return {
        "classification": REAL_EVIDENCE,
        "operations_id": OPERATIONS_ID,
        "scheduled_games": len(scheduled),
        "accounted_for_games": sum(
            value in accounted_states for value in latest.values()
        ),
        "capture_attempts": len(attempts),
        "accepted_decisions": len(state.decisions),
        "rejected_captures": sum(e.get("status") == "rejected" for e in attempts),
        "unavailable_games": sum(value == "unavailable" for value in latest.values()),
        "pending_games": sum(
            value in {"pending", "scheduled", "postponed"} for value in latest.values()
        ),
        "non_bets": ledger["non_bets"],
        "eligible_bets": ledger["bets"],
        "unsettled_bets": ledger["unsettled_bets"],
        "settlement_exceptions": len(audit["overdue_settlements"]),
        "integrity_failures": 0,
        "missing_games": audit["unaccounted_games"],
        "prospective_evidence_count": len(state.decisions),
        "terminal_hash": audit["terminal_hash"],
    }


def game_day_checklist() -> dict[str, list[dict[str, str]]]:
    """Return objective checks operators must satisfy at each stage."""
    return {
        "before_capture": [
            {
                "check": "canonical_game",
                "rule": "scheduled 2026 REG Week 1-16 canonical ID",
            },
            {"check": "pre_kickoff", "rule": "receipt_at < kickoff_at"},
            {"check": "capture_window", "rule": "55-65 minutes before kickoff"},
        ],
        "at_capture": [
            {
                "check": "seven_books",
                "rule": "all frozen consensus books have both prices",
            },
            {
                "check": "fresh_quotes",
                "rule": "age <= 10 minutes and not after receipt",
            },
            {"check": "def_epa", "rule": "Week 1 null -> 0.0; Weeks 2-16 finite"},
            {"check": "execution", "rule": "DraftKings executable price retained"},
            {
                "check": "raw_retention",
                "rule": "content-addressed SHA256 artifact exists",
            },
        ],
        "after_capture": [
            {"check": "manifest", "rule": "attempt status and reason are append-only"},
            {
                "check": "ledger",
                "rule": "accepted decision appended once through Step 91C",
            },
            {"check": "integrity", "rule": "manifest chain and ledger replay validate"},
        ],
    }


def dry_run(workspace: Path | str) -> dict[str, Any]:
    """Exercise the full workflow only inside an explicitly isolated directory."""
    root = Path(workspace)
    if root.exists() and any(root.iterdir()):
        raise ProspectiveOperationsError("dry-run workspace must be empty")
    root.mkdir(parents=True, exist_ok=True)
    game_id = "2026_01_TST_AAA"
    kickoff = datetime(2026, 9, 13, 17, tzinfo=UTC)
    receipt = kickoff - timedelta(minutes=60)
    schedule = [
        {
            "game_id": game_id,
            "season": 2026,
            "season_type": "REG",
            "week": 1,
            "kickoff_at": _utc_text(kickoff),
            "home_team": "AAA",
            "away_team": "TST",
            "provider_ids": ["DRY-RUN-ONLY"],
        }
    ]
    offers = [
        {
            "book": book,
            "market": "moneyline",
            "home_team": "AAA",
            "away_team": "TST",
            "home_odds": 120,
            "away_odds": -140,
            "observed_at": _utc_text(receipt - timedelta(minutes=5)),
        }
        for book in CONSENSUS_BOOKS
    ]
    snapshot = {
        "schema_version": 1,
        "provider": "SYNTHETIC_TEST_FIXTURE",
        "captured_at": _utc_text(receipt),
        "game": {
            key: value for key, value in schedule[0].items() if key != "provider_ids"
        },
        "def_epa": None,
        "offers": offers,
    }
    schedule_path = root / "synthetic_schedule.json"
    raw_path = root / "synthetic_capture.json"
    result_path = root / "synthetic_official_result.txt"
    schedule_path.write_text(canonical_json(schedule), encoding="utf-8", newline="\n")
    raw_path.write_text(canonical_json(snapshot), encoding="utf-8", newline="\n")
    result_path.write_text("SYNTHETIC HOME FINAL", encoding="utf-8", newline="\n")
    manifest = root / "synthetic_manifest.jsonl"
    ledger = root / "synthetic_ledger.jsonl"
    initialize_manifest(schedule_path, manifest)
    captured = capture_game(
        manifest,
        ledger,
        raw_path,
        root / "synthetic_raw",
        game_id=game_id,
        receipt_at=_utc_text(receipt),
    )
    settled = settle_game(
        manifest,
        ledger,
        game_id=game_id,
        result="HOME",
        final_at=_utc_text(kickoff + timedelta(hours=3)),
        settled_at=_utc_text(kickoff + timedelta(hours=3)),
        result_source=result_path,
    )
    summary = operational_summary(
        manifest, ledger, as_of=_utc_text(kickoff + timedelta(hours=4))
    )
    return {
        "classification": DRY_RUN_EVIDENCE,
        "warning": "SYNTHETIC TEST DATA; NEVER REAL PROSPECTIVE EVIDENCE",
        "isolated_workspace": str(root),
        "capture_status": captured["attempt"]["status"],
        "decision_recorded": captured["decision"] is not None,
        "settlement_recorded": settled["event_type"] == "SETTLEMENT",
        "integrity_valid": True,
        "summary": {**summary, "classification": DRY_RUN_EVIDENCE},
    }


__all__ = [
    "DRY_RUN_EVIDENCE",
    "FROZEN_PROTOCOL",
    "OPERATIONS_ID",
    "ProspectiveOperationsError",
    "assert_frozen_protocol",
    "capture_game",
    "dry_run",
    "game_day_checklist",
    "initialize_manifest",
    "operational_summary",
    "record_game_status",
    "settle_game",
]
