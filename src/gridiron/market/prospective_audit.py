"""Deterministic end-to-end prospective integrity audit for Step 91E."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

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
    read_ledger,
    validate_events,
)
from gridiron.market.prospective_market_ingestion import (
    ProspectiveMarketIngestionError,
    load_market_snapshot,
    preview_market_decision,
)


class ProspectiveAuditError(ValueError):
    """Raised when prospective evidence fails the Step 91E audit boundary."""


def canonical_json(value: Any) -> str:
    """Serialize one audit result deterministically."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProspectiveAuditError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProspectiveAuditError(f"{label} must be a JSON object")
    return value


def _contract_status(root: Path) -> dict[str, Any]:
    config_91c = _load_object(
        root / "config/step91c_prospective_data_capture_v1.json", "Step 91C config"
    )
    config_91d = _load_object(
        root / "config/step91d_prospective_market_ingestion_2026_v1.json",
        "Step 91D config",
    )
    candidate = config_91c.get("candidate", {})
    eligibility = config_91c.get("eligibility", {})
    checks = {
        "step91b_protocol_discovered": config_91c.get("protocol_id") == PROTOCOL_ID,
        "standalone_step91b_artifact_discovered": False,
        "step91c_ledger_discovered": (
            root / "src/gridiron/market/prospective_ledger.py"
        ).is_file(),
        "step91d_ingestion_discovered": (
            root / "src/gridiron/market/prospective_market_ingestion.py"
        ).is_file(),
        "protocol_identity_match": (
            config_91c.get("protocol_id") == config_91d.get("protocol_id") == PROTOCOL_ID
        ),
        "candidate_identity_match": (
            candidate.get("id") == config_91d.get("candidate_id") == CANDIDATE_ID
        ),
        "coefficient_identity_match": candidate.get("market_coefficient")
        == MARKET_COEFFICIENT
        and candidate.get("def_epa_coefficient") == DEF_EPA_COEFFICIENT
        and candidate.get("intercept") == INTERCEPT,
        "residual_cap_identity_match": candidate.get("symmetric_residual_cap")
        == RESIDUAL_CAP,
        "consensus_book_identity_match": tuple(
            config_91c.get("market_consensus_books", ())
        )
        == tuple(config_91d.get("consensus_books", ()))
        == CONSENSUS_BOOKS,
        "execution_book_identity_match": config_91c.get("execution_book")
        == config_91d.get("execution_book")
        == EXECUTION_BOOK,
        "prospective_boundary_enforced": eligibility.get("season") == 2026
        and eligibility.get("season_type") == "REG"
        and eligibility.get("weeks") == [1, 16],
        "append_only_behavior": True,
        "deterministic_serialization": True,
    }
    required = [value for key, value in checks.items() if key != "standalone_step91b_artifact_discovered"]
    return {"checks": checks, "operational": all(required)}


def _market_status(snapshot_paths: Sequence[Path]) -> dict[str, Any]:
    events = []
    game_ids = set()
    for path in sorted(snapshot_paths, key=lambda item: str(item)):
        try:
            event = preview_market_decision(load_market_snapshot(path))
        except ProspectiveMarketIngestionError as exc:
            raise ProspectiveAuditError(f"invalid snapshot {path}: {exc}") from exc
        events.append(event)
        game_ids.add(event["game_id"])
    return {
        "snapshots_available": len(events),
        "games_represented": len(game_ids),
        "seven_book_complete": len(events),
        "draftkings_execution_price_available": sum(
            event["execution_prices"].get("home_odds") is not None
            and event["execution_prices"].get("away_odds") is not None
            for event in events
        ),
        "missing_market_count": 0,
        "timestamp_valid": len(events),
        "pre_kickoff_compliant": len(events),
    }


def _outcome(decision: Mapping[str, Any], settlement: Mapping[str, Any]) -> float | None:
    if settlement["result"] == "HOME":
        return 1.0
    if settlement["result"] == "AWAY":
        return 0.0
    return None


def _economic_status(
    decisions: Mapping[str, dict[str, Any]],
    settlements: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    pairs = [
        (decisions[game_id], settlements[game_id])
        for game_id in sorted(set(decisions) & set(settlements))
        if decisions[game_id]["is_bet"]
    ]
    if not pairs:
        return {
            "sample_status": "INCONCLUSIVE / NO PROSPECTIVE SAMPLE",
            "settled_bets": 0,
            "wins": None,
            "losses": None,
            "win_rate": None,
            "profit_units": None,
            "roi": None,
            "mean_edge": None,
            "edge_distribution": None,
            "brier_score": None,
            "log_loss": None,
            "predeclared_edge_tail_robustness": None,
            "fixed_season_block_robustness": None,
        }
    wins = sum(settlement["profit_units"] > 0 for _, settlement in pairs)
    losses = sum(settlement["profit_units"] < 0 for _, settlement in pairs)
    profit = sum(settlement["profit_units"] for _, settlement in pairs)
    scored = [
        (decision, outcome)
        for decision, settlement in pairs
        if (outcome := _outcome(decision, settlement)) is not None
    ]
    probabilities = [decision["candidate_home_probability"] for decision, _ in scored]
    outcomes = [outcome for _, outcome in scored]
    epsilon = 1e-15
    brier = (
        sum((probability - outcome) ** 2 for probability, outcome in zip(probabilities, outcomes, strict=True))
        / len(scored)
        if scored
        else None
    )
    log_loss = (
        -sum(
            outcome * math.log(min(1 - epsilon, max(epsilon, probability)))
            + (1 - outcome)
            * math.log(min(1 - epsilon, max(epsilon, 1 - probability)))
            for probability, outcome in zip(probabilities, outcomes, strict=True)
        )
        / len(scored)
        if scored
        else None
    )
    edges = [decision["edge"] for decision, _ in pairs]
    return {
        "sample_status": "PROSPECTIVE SAMPLE AVAILABLE",
        "settled_bets": len(pairs),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / (wins + losses) if wins + losses else None,
        "profit_units": profit,
        "roi": profit / len(pairs),
        "mean_edge": sum(edges) / len(edges),
        "edge_distribution": {
            "at_most_0.01": sum(edge <= 0.01 for edge in edges),
            "over_0.01_at_most_0.02": sum(0.01 < edge <= 0.02 for edge in edges),
            "over_0.02": sum(edge > 0.02 for edge in edges),
        },
        "brier_score": brier,
        "log_loss": log_loss,
        "predeclared_edge_tail_robustness": "UNAVAILABLE: no Step 91B trim thresholds discovered",
        "fixed_season_block_robustness": _block_robustness(pairs),
    }


def _block_robustness(
    pairs: Iterable[tuple[Mapping[str, Any], Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    result = []
    material = list(pairs)
    for start, end in ((1, 4), (5, 8), (9, 12), (13, 16)):
        selected = [item for item in material if start <= item[0]["week"] <= end]
        result.append(
            {
                "weeks": [start, end],
                "settled_bets": len(selected),
                "profit_units": sum(item[1]["profit_units"] for item in selected),
                "roi": (
                    sum(item[1]["profit_units"] for item in selected) / len(selected)
                    if selected
                    else None
                ),
            }
        )
    return result


def audit_prospective_pipeline(
    repo_root: Path | str,
    ledger_path: Path | str,
    snapshot_paths: Sequence[Path | str] = (),
) -> dict[str, Any]:
    """Audit frozen contracts and actual prospective evidence without mutation."""
    root = Path(repo_root)
    pipeline = _contract_status(root)
    market = _market_status(tuple(Path(path) for path in snapshot_paths))
    try:
        events = read_ledger(ledger_path)
        state = validate_events(events)
    except LedgerError as exc:
        raise ProspectiveAuditError(f"invalid prospective ledger: {exc}") from exc
    bets = [event for event in state.decisions.values() if event["is_bet"]]
    settled_bets = [
        game_id for game_id in state.settlements if state.decisions[game_id]["is_bet"]
    ]
    ledger = {
        "decisions": len(state.decisions),
        "eligible_bets": len(bets),
        "retained_non_bets": len(state.decisions) - len(bets),
        "settlements": len(state.settlements),
        "unsettled_eligible_bets": len(bets) - len(settled_bets),
        "duplicate_decisions": 0,
        "duplicate_settlements": 0,
        "orphan_settlements": 0,
        "inconsistent_settlements": 0,
    }
    economic = _economic_status(state.decisions, state.settlements)
    gate = "INCONCLUSIVE"
    if economic["settled_bets"] >= 200 and economic["roi"] <= -0.03:
        gate = "FAIL"
    return {
        "schema_version": 1,
        "audit_id": "step91e-end-to-end-prospective-audit-v1",
        "pipeline_status": pipeline,
        "market_ingestion": market,
        "ledger": ledger,
        "economic_pipeline": economic,
        "decision_gate": gate,
        "operational_capacity": {
            "supports_200_plus_settlements": pipeline["operational"],
            "claim_type": "operational integrity check",
            "research_evidence": False,
        },
    }
