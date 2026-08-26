"""Operational accumulation of genuine Step 91F prospective evidence."""

from __future__ import annotations

import json
import math
import statistics
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from gridiron.market.prospective_audit import canonical_json
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
    settle_decision,
    validate_ledger,
)
from gridiron.market.prospective_market_ingestion import (
    ProspectiveMarketIngestionError,
    capture_market_decision,
    load_market_snapshot,
)

REAL_EVIDENCE = "REAL PROSPECTIVE DATA"
FIXTURE_EVIDENCE = "TEST FIXTURES / SYNTHETIC DATA"
MINIMUM_SETTLED_BETS = 200
FAIL_ROI = -0.03
PROMOTION_ROI = 0.02
SEASON_MINIMUM_BETS = 50
SEASON_FAIL_ROI = -0.05


class ProspectiveEvidenceError(ValueError):
    """Raised when Step 91F cannot accept or summarize evidence."""


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProspectiveEvidenceError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProspectiveEvidenceError(f"{label} must be a JSON object")
    return value


def protocol_completeness(repo_root: Path | str) -> dict[str, Any]:
    """Report every frozen component required to operate and evaluate the gate."""
    root = Path(repo_root)
    config_91c = _load_object(
        root / "config/step91c_prospective_data_capture_v1.json", "Step 91C config"
    )
    config_91e = _load_object(
        root / "config/step91e_end_to_end_prospective_audit_v1.json",
        "Step 91E config",
    )
    candidate = config_91c.get("candidate", {})
    eligibility = config_91c.get("eligibility", {})
    gates = config_91e.get("decision_gates", {})
    edge_trims = config_91e.get("predeclared_edge_trims")
    components = {
        "protocol_identity": config_91c.get("protocol_id") == PROTOCOL_ID,
        "candidate_identity": candidate.get("id") == CANDIDATE_ID,
        "candidate_version": CANDIDATE_ID.endswith("-v1"),
        "coefficients": candidate.get("market_coefficient") == MARKET_COEFFICIENT
        and candidate.get("def_epa_coefficient") == DEF_EPA_COEFFICIENT
        and candidate.get("intercept") == INTERCEPT,
        "residual_cap": candidate.get("symmetric_residual_cap") == RESIDUAL_CAP,
        "market_books": tuple(config_91c.get("market_consensus_books", ()))
        == CONSENSUS_BOOKS,
        "execution_book": config_91c.get("execution_book") == EXECUTION_BOOK,
        "eligibility_rule": eligibility.get("edge") == "strictly-positive",
        "population_boundary": eligibility.get("season") == 2026
        and eligibility.get("season_type") == "REG"
        and eligibility.get("weeks") == [1, 16],
        "decision_timestamp_rule": True,
        "settlement_rule": True,
        "primary_metrics": True,
        "minimum_sample_size": gates.get("minimum_settled_bets")
        == MINIMUM_SETTLED_BETS,
        "failure_gate": gates.get("fail_roi_at_or_below") == FAIL_ROI,
        "promotion_gate": gates.get("promotion_minimum_roi") == PROMOTION_ROI
        and gates.get("promotion_requires_positive_profit") is True,
        "edge_trim_thresholds": isinstance(edge_trims, list) and bool(edge_trims),
        "season_robustness_rule": gates.get("season_minimum_bets")
        == SEASON_MINIMUM_BETS
        and gates.get("season_fail_roi_at_or_below") == SEASON_FAIL_ROI,
    }
    missing = [name for name, available in components.items() if not available]
    return {
        "status": "COMPLETE" if not missing else "INCOMPLETE",
        "components": components,
        "missing_components": missing,
        "edge_trim_threshold_status": (
            "AVAILABLE" if components["edge_trim_thresholds"] else "MISSING — NOT AUTHORITATIVELY FROZEN"
        ),
    }


def capture_real_snapshot(
    ledger_path: Path | str,
    snapshot_path: Path | str,
    *,
    evidence_classification: str = REAL_EVIDENCE,
) -> dict[str, Any]:
    """Capture one genuine snapshot through Step 91D and Step 91C unchanged."""
    if evidence_classification != REAL_EVIDENCE:
        raise ProspectiveEvidenceError(
            "only REAL PROSPECTIVE DATA may be captured in the operational ledger"
        )
    try:
        raw = load_market_snapshot(snapshot_path)
        return capture_market_decision(ledger_path, raw)
    except ProspectiveMarketIngestionError as exc:
        raise ProspectiveEvidenceError(f"snapshot capture rejected: {exc}") from exc


def settle_real_observation(
    ledger_path: Path | str,
    *,
    game_id: str,
    result: str,
    settled_at: str,
) -> dict[str, Any]:
    """Settle an existing decision through Step 91C using its captured price."""
    try:
        return settle_decision(
            ledger_path, game_id=game_id, result=result, settled_at=settled_at
        )
    except LedgerError as exc:
        raise ProspectiveEvidenceError(f"settlement rejected: {exc}") from exc


def evaluate_gate(
    *,
    settled_bets: int,
    profit_units: float,
    season_summaries: Sequence[Mapping[str, Any]],
    edge_trim_profits: Sequence[float] | None,
) -> dict[str, Any]:
    """Apply only the documented Step 91B gates without choosing trim thresholds."""
    roi = profit_units / settled_bets if settled_bets else None
    if settled_bets < MINIMUM_SETTLED_BETS:
        status = "INCONCLUSIVE"
        reason = "fewer than 200 settled bets"
    elif roi is not None and roi <= FAIL_ROI:
        status = "FAIL"
        reason = "at least 200 settled bets and ROI is at or below -3%"
    else:
        bad_season = any(
            item["settled_bets"] >= SEASON_MINIMUM_BETS
            and item["roi"] is not None
            and item["roi"] <= SEASON_FAIL_ROI
            for item in season_summaries
        )
        if edge_trim_profits is None:
            status = "INCONCLUSIVE"
            reason = "authoritative edge-trim thresholds are missing"
        elif (
            profit_units > 0
            and roi is not None
            and roi >= PROMOTION_ROI
            and all(profit > 0 for profit in edge_trim_profits)
            and not bad_season
        ):
            status = "PROMOTION CANDIDATE"
            reason = "all documented promotion conditions are satisfied"
        else:
            status = "INCONCLUSIVE"
            reason = "neither post-sample gate is satisfied"
    return {"status": status, "reason": reason, "roi": roi}


def _economic_metrics(
    decisions: Mapping[str, dict[str, Any]],
    settlements: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    eligible = [decision for decision in decisions.values() if decision["is_bet"]]
    pairs = [
        (decisions[game_id], settlements[game_id])
        for game_id in sorted(set(decisions) & set(settlements))
        if decisions[game_id]["is_bet"]
    ]
    wins = sum(settlement["profit_units"] > 0 for _, settlement in pairs)
    losses = sum(settlement["profit_units"] < 0 for _, settlement in pairs)
    profit = sum(settlement["profit_units"] for _, settlement in pairs)
    scored = []
    for decision, settlement in pairs:
        if settlement["result"] in {"HOME", "AWAY"}:
            outcome = 1.0 if settlement["result"] == "HOME" else 0.0
            scored.append((decision["candidate_home_probability"], outcome))
    epsilon = 1e-15
    brier = (
        sum((probability - outcome) ** 2 for probability, outcome in scored)
        / len(scored)
        if scored
        else None
    )
    log_loss = (
        -sum(
            outcome * math.log(min(1 - epsilon, max(epsilon, probability)))
            + (1 - outcome) * math.log(min(1 - epsilon, max(epsilon, 1 - probability)))
            for probability, outcome in scored
        )
        / len(scored)
        if scored
        else None
    )
    edges = [decision["edge"] for decision in eligible]
    odds = [decision["selected_execution_odds"] for decision in eligible]
    return {
        "settled_bets": len(pairs),
        "unsettled_bets": len(eligible) - len(pairs),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / (wins + losses) if wins + losses else None,
        "profit_units": profit if pairs else None,
        "roi": profit / len(pairs) if pairs else None,
        "mean_edge": statistics.fmean(edges) if edges else None,
        "median_edge": statistics.median(edges) if edges else None,
        "brier_score": brier,
        "log_loss": log_loss,
        "offered_odds_distribution": (
            {
                "count": len(odds),
                "minimum": min(odds),
                "median": statistics.median(odds),
                "maximum": max(odds),
            }
            if odds
            else None
        ),
    }


def evidence_summary(repo_root: Path | str, ledger_path: Path | str) -> dict[str, Any]:
    """Return deterministic real-evidence progress without changing the ledger."""
    try:
        state = validate_ledger(ledger_path)
    except LedgerError as exc:
        raise ProspectiveEvidenceError(f"invalid prospective ledger: {exc}") from exc
    metrics = _economic_metrics(state.decisions, state.settlements)
    completeness = protocol_completeness(repo_root)
    season_summary = [
        {
            "season": 2026,
            "settled_bets": metrics["settled_bets"],
            "profit_units": metrics["profit_units"],
            "roi": metrics["roi"],
        }
    ]
    gate = evaluate_gate(
        settled_bets=metrics["settled_bets"],
        profit_units=metrics["profit_units"] or 0.0,
        season_summaries=season_summary,
        edge_trim_profits=None,
    )
    weeks = [decision["week"] for decision in state.decisions.values()]
    return {
        "schema_version": 1,
        "operation_id": "step91f-prospective-evidence-accumulation-v1",
        "evidence_classification": REAL_EVIDENCE,
        "fixtures_included": False,
        "games_evaluated": len(state.decisions),
        "decisions": len(state.decisions),
        "eligible_bets": sum(
            decision["is_bet"] for decision in state.decisions.values()
        ),
        "non_bets": sum(
            not decision["is_bet"] for decision in state.decisions.values()
        ),
        **metrics,
        "season_progress": {
            "season": 2026,
            "eligible_weeks": [1, 16],
            "latest_evaluated_week": max(weeks) if weeks else None,
        },
        "settled_bets_toward_200": min(metrics["settled_bets"], 200),
        "settled_bets_remaining": max(0, 200 - metrics["settled_bets"]),
        "gate": gate,
        "protocol_completeness": completeness,
    }


def validate_real_ledger(ledger_path: Path | str) -> dict[str, Any]:
    """Validate a real ledger and return deterministic counts."""
    try:
        state = validate_ledger(ledger_path)
    except LedgerError as exc:
        raise ProspectiveEvidenceError(f"invalid prospective ledger: {exc}") from exc
    return {
        "valid": True,
        "evidence_classification": REAL_EVIDENCE,
        "decisions": len(state.decisions),
        "settlements": len(state.settlements),
    }


__all__ = [
    "FIXTURE_EVIDENCE",
    "REAL_EVIDENCE",
    "ProspectiveEvidenceError",
    "canonical_json",
    "capture_real_snapshot",
    "evaluate_gate",
    "evidence_summary",
    "protocol_completeness",
    "settle_real_observation",
    "validate_real_ledger",
]
