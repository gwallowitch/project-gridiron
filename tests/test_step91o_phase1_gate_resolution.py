from __future__ import annotations

import json
from pathlib import Path

from gridiron.market.prospective_ledger import (
    CANDIDATE_ID,
    CONSENSUS_BOOKS,
    DEF_EPA_COEFFICIENT,
    EXECUTION_BOOK,
    INTERCEPT,
    MARKET_COEFFICIENT,
    RESIDUAL_CAP,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "research/governance/step91o/step91o_phase1_gate_resolution.json"
STEP91I_CONFIG = ROOT / "config/step91i_prospective_collection_operations_v1.json"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_phase1_remains_non_evidence_and_blocks_activation() -> None:
    report = load_json(REPORT)
    assert report["step"] == "STEP 91O"
    assert report["phase"] == 1
    assert report["classification"] == "NON-PROSPECTIVE / NON-EVIDENCE"
    assert report["protocol"]["activation_allowed"] is False
    assert report["commercial"]["spent_usd"] == 0
    assert report["commercial"]["plan_purchased"] is False
    assert report["evidence_boundary"] == {
        "prospective_evidence_count": 0,
        "real_manifest_touched": False,
        "real_ledger_touched": False,
        "qualifying_capture": False,
        "settlement": False,
        "outcomes_used": False,
        "historical_optimization": False,
    }
    assert any(
        gate["blocking"] and gate["status"] != "PASS"
        for gate in report["gates"]
    )


def test_phase1_contract_is_core_four_fail_closed_and_single_provider() -> None:
    report = load_json(REPORT)
    assert report["protocol"]["books"] == [
        "BetMGM",
        "FanDuel",
        "DraftKings",
        "Caesars",
    ]
    assert report["provider_mapping"] == {
        "BetMGM": "betmgm",
        "FanDuel": "fanduel",
        "DraftKings": "draftkings",
        "Caesars": "williamhill_us",
    }
    contract = report["contracts"]
    assert contract["atomic_single_response"] is True
    assert contract["cross_call_assembly"] is False
    assert contract["all_four_moneylines_required"] is True
    assert contract["three_of_four_allowed"] is False
    assert contract["imputation_allowed"] is False
    assert contract["backup_provider"] is None
    assert contract["provider_failure"] == "REJECT_ATTEMPT"


def test_phase1_does_not_rewrite_frozen_step91c_to_step91i_contract() -> None:
    assert CANDIDATE_ID == "market-plus-def-epa-capped-0425-v1"
    assert MARKET_COEFFICIENT == 4.980172
    assert DEF_EPA_COEFFICIENT == 1.044827
    assert INTERCEPT == -2.514766
    assert RESIDUAL_CAP == 0.0425
    assert EXECUTION_BOOK == "DraftKings"
    assert CONSENSUS_BOOKS == (
        "Bet365",
        "SI",
        "Betway",
        "BetMGM",
        "FanDuel",
        "Caesars",
        "DraftKings",
    )
    step91i = load_json(STEP91I_CONFIG)
    assert step91i["protocol_id"] == "step91b-prospective-validation-v1"
    assert step91i["capture"]["complete_seven_book_input"] is True
    assert step91i["real_evidence"]["initial_observations"] == 0
