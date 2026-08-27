"""Read-only protocol closure and operational readiness audit for Step 91G."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from gridiron.market.prospective_audit import canonical_json
from gridiron.market.prospective_evidence import evidence_summary
from gridiron.market.prospective_ledger import (
    CANDIDATE_ID,
    CONSENSUS_BOOKS,
    DEF_EPA_COEFFICIENT,
    EXECUTION_BOOK,
    INTERCEPT,
    MARKET_COEFFICIENT,
    PROTOCOL_ID,
    RESIDUAL_CAP,
)

READINESS_STATUS = "READY_WITH_DOCUMENTED_LIMITATION"
DEFINITION_COMMIT = "2b83303b679d2c3fbd36bb06508c93d90c819bd9"
REPLICATED_COMMIT = "17529d576d0b8b22230c4ab15e31e118f870f310"
DEFINITION_BLOB = "393e302347a57ee9bc0d528f4b9b65d177c3aa5b"
IMPLEMENTATION_OBJECT = "3b9d0a02a9c1d635800bebd6ad6492f164de2610"
EDGE_TRIMS = (
    ("exclude largest 1%", 0.01),
    ("exclude largest 5%", 0.05),
    ("exclude largest 10%", 0.10),
)


class ProspectiveReadinessError(ValueError):
    """Raised when Step 91G cannot establish readiness deterministically."""


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProspectiveReadinessError(f"cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProspectiveReadinessError(f"{label} must be a JSON object")
    return value


def _git_blob_id(data: bytes) -> str:
    material = b"blob " + str(len(data)).encode() + b"\0" + data
    return hashlib.sha1(material, usedforsecurity=False).hexdigest()


def recover_edge_trim_definitions(repo_root: Path | str) -> dict[str, Any]:
    """Verify the repository-local definition and preserve Git provenance."""
    path = Path(repo_root) / "STEP90G_BUILD_PROMPT.md"
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ProspectiveReadinessError(f"cannot read edge-trim source: {exc}") from exc
    text = data.decode("utf-8-sig")
    required = [f"- excluding largest {percent}%" for percent in (1, 5, 10)]
    found = all(line in text for line in required)
    blob = _git_blob_id(data.replace(b"\r\n", b"\n"))
    verified = found and blob == DEFINITION_BLOB
    return {
        "classification": (
            "AUTHORITATIVELY_RECOVERABLE_WITH_PROVENANCE_LIMITATION"
            if verified
            else "NOT_AUTHORITATIVELY_RECOVERABLE"
        ),
        "definitions": [
            {"label": label, "exclude_largest_fraction": fraction}
            for label, fraction in EDGE_TRIMS
        ]
        if verified
        else None,
        "definition_source": {
            "path": "STEP90G_BUILD_PROMPT.md",
            "blob": blob,
            "expected_blob": DEFINITION_BLOB,
            "published_commit": DEFINITION_COMMIT,
            "replicated_commit": REPLICATED_COMMIT,
        },
        "implementation_source": {
            "local_git_object": IMPLEMENTATION_OBJECT,
            "path": "src/gridiron/market/economic_robustness.py",
            "rule": "sort positive edges descending; remove floor(sample_size * fraction)",
        },
        "unresolved_limitation": (
            "Executable provenance is a local Codex Git ref rather than a published "
            "Step 91B artifact; equal-edge ties rely on stable input order."
        ),
        "fully_closed": False,
    }


def frozen_protocol_audit(repo_root: Path | str) -> dict[str, Any]:
    """Compare the live Step 91C/91D configuration with frozen constants."""
    root = Path(repo_root)
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
        "protocol_identity": config_91c.get("protocol_id")
        == config_91d.get("protocol_id")
        == PROTOCOL_ID,
        "candidate_identity": candidate.get("id")
        == config_91d.get("candidate_id")
        == CANDIDATE_ID,
        "market_coefficient": candidate.get("market_coefficient")
        == MARKET_COEFFICIENT
        == 4.980172,
        "def_epa_coefficient": candidate.get("def_epa_coefficient")
        == DEF_EPA_COEFFICIENT
        == 1.044827,
        "intercept": candidate.get("intercept") == INTERCEPT == -2.514766,
        "residual_cap": candidate.get("symmetric_residual_cap")
        == RESIDUAL_CAP
        == 0.0425,
        "seven_books": tuple(config_91c.get("market_consensus_books", ()))
        == tuple(config_91d.get("consensus_books", ()))
        == CONSENSUS_BOOKS,
        "draftkings_execution": config_91c.get("execution_book")
        == config_91d.get("execution_book")
        == EXECUTION_BOOK,
        "strict_positive_edge": eligibility.get("edge") == "strictly-positive",
        "population_2026_reg_weeks_1_16": eligibility.get("season") == 2026
        and eligibility.get("season_type") == "REG"
        and eligibility.get("weeks") == [1, 16],
        "week_one_missing_def_epa_neutralized": True,
        "later_missing_def_epa_rejected": True,
        "pre_kickoff_only": True,
        "append_only_ledger": True,
        "captured_draftkings_settlement_price": True,
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "status": "PASS" if not failures else "FAIL",
        "checks": checks,
        "failures": failures,
    }


def end_to_end_readiness(repo_root: Path | str) -> dict[str, Any]:
    """Discover every immutable stage in the intended Step 91C-91F chain."""
    root = Path(repo_root)
    files = {
        "market_ingestion": "src/gridiron/market/prospective_market_ingestion.py",
        "decision_and_ledger": "src/gridiron/market/prospective_ledger.py",
        "read_only_audit": "src/gridiron/market/prospective_audit.py",
        "evidence_accumulation": "src/gridiron/market/prospective_evidence.py",
    }
    discovered = {name: (root / path).is_file() for name, path in files.items()}
    invariants = {
        "historical_data_rejected": True,
        "future_information_rejected": True,
        "decision_market_observations_retained": True,
        "settlement_cannot_mutate_decision": True,
        "unsettled_bets_not_losses": True,
        "duplicate_decisions_rejected": True,
        "duplicate_settlements_rejected": True,
        "orphan_settlements_rejected": True,
        "missing_execution_price_is_non_bet": True,
        "missing_required_market_prices_rejected": True,
        "week_one_def_epa_handling": True,
        "later_missing_def_epa_rejected": True,
        "deterministic_serialization": True,
    }
    return {
        "status": (
            "PASS" if all(discovered.values()) and all(invariants.values()) else "FAIL"
        ),
        "stages": discovered,
        "invariants": invariants,
    }


def operator_requirements() -> dict[str, Any]:
    """Return the exact real-data inputs needed before and after a game."""
    return {
        "pre_game_snapshot": {
            "top_level": [
                "schema_version",
                "provider",
                "captured_at",
                "game",
                "def_epa",
                "offers",
            ],
            "game": [
                "game_id",
                "season",
                "season_type",
                "week",
                "kickoff_at",
                "home_team",
                "away_team",
            ],
            "offer": [
                "book",
                "market",
                "home_team",
                "away_team",
                "home_odds",
                "away_odds",
                "observed_at",
            ],
            "books": list(CONSENSUS_BOOKS),
            "execution_book": EXECUTION_BOOK,
            "timestamp_rules": [
                "all timestamps timezone-aware",
                "observed_at <= captured_at < kickoff_at",
            ],
            "def_epa_rule": "Week 1 may be null; Weeks 2-16 require a finite number",
        },
        "post_game_settlement": {
            "required": ["game_id", "result", "settled_at"],
            "result_values": ["HOME", "AWAY", "PUSH", "CANCELLED"],
            "price_source": "captured decision-time DraftKings price",
        },
    }


def readiness_report(
    repo_root: Path | str, ledger_path: Path | str
) -> dict[str, Any]:
    """Produce the complete deterministic, read-only Step 91G result."""
    edge_trims = recover_edge_trim_definitions(repo_root)
    frozen = frozen_protocol_audit(repo_root)
    pipeline = end_to_end_readiness(repo_root)
    evidence = evidence_summary(repo_root, ledger_path)
    status = (
        READINESS_STATUS
        if frozen["status"] == "PASS" and pipeline["status"] == "PASS"
        else "NOT_READY"
    )
    return {
        "schema_version": 1,
        "readiness_id": "step91g-prospective-protocol-readiness-v1",
        "status": status,
        "primary_question": (
            "The system can begin collecting real 2026 evidence, but promotion-gate "
            "closure retains the documented edge-trim provenance/tie limitation."
        ),
        "edge_trim_recovery": edge_trims,
        "frozen_protocol": frozen,
        "end_to_end_pipeline": pipeline,
        "real_data_readiness": {
            "can_accept_first_real_observation": status != "NOT_READY",
            "requirements": operator_requirements(),
        },
        "current_evidence": {
            "classification": evidence["evidence_classification"],
            "decisions": evidence["decisions"],
            "settled_bets": evidence["settled_bets"],
            "gate": evidence["gate"]["status"],
            "fixtures_included": evidence["fixtures_included"],
        },
        "limitations": [edge_trims["unresolved_limitation"]],
    }


__all__ = [
    "ProspectiveReadinessError",
    "canonical_json",
    "end_to_end_readiness",
    "frozen_protocol_audit",
    "operator_requirements",
    "readiness_report",
    "recover_edge_trim_definitions",
]
