"""Read-only Step 91W execution economics and performance accounting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from statistics import fmean
from typing import Any

from gridiron.market.closing_settlement import (
    FUNDING_TYPES,
    ClosingSettlementError,
    read_executions,
    read_settlements,
)

CLASSIFICATION = "NON_PROSPECTIVE_OPERATIONAL_PERFORMANCE_ACCOUNTING"


class PerformanceAccountingError(ValueError):
    """Execution economics cannot be reported safely."""


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise PerformanceAccountingError(f"{field} must be an ISO-8601 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise PerformanceAccountingError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise PerformanceAccountingError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def execution_funding_type(execution: Mapping[str, Any]) -> str:
    """Normalize legacy schema-v1 executions to their frozen CASH meaning."""
    funding_type = (
        "CASH" if execution.get("schema_version") == 1 else execution.get("funding_type")
    )
    if funding_type not in FUNDING_TYPES:
        raise PerformanceAccountingError("execution has an unsupported funding type")
    return str(funding_type)


def _mean(values: Sequence[float]) -> float | None:
    return None if not values else fmean(values)


def _week(game_id: str) -> int:
    try:
        return int(game_id.split("_")[1])
    except (IndexError, ValueError) as exc:
        raise PerformanceAccountingError("execution has invalid canonical week") from exc


def build_performance_report(
    execution_path: object,
    settlement_path: object,
    *,
    through: datetime | None = None,
    game_id: str | None = None,
    week: int | None = None,
    funding_type: str | None = None,
    starting_cash: float | None = None,
    starting_bonus: float | None = None,
) -> dict[str, Any]:
    """Read validated ledgers and produce descriptive, non-optimizing economics."""
    if funding_type is not None and funding_type not in FUNDING_TYPES:
        raise PerformanceAccountingError("funding_type must be CASH or BONUS_BET")
    if week is not None and not 1 <= week <= 16:
        raise PerformanceAccountingError("week must be between 1 and 16")
    for value, field in ((starting_cash, "starting_cash"), (starting_bonus, "starting_bonus")):
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0
        ):
            raise PerformanceAccountingError(f"{field} must be nonnegative")
    cutoff = None
    if through is not None:
        if through.tzinfo is None:
            raise PerformanceAccountingError("through must include a timezone")
        cutoff = through.astimezone(UTC)
    try:
        executions = read_executions(execution_path)
        settlements = read_settlements(settlement_path)
    except (ClosingSettlementError, OSError) as exc:
        raise PerformanceAccountingError(str(exc)) from exc
    if cutoff is not None:
        executions = tuple(
            row
            for row in executions
            if _timestamp(row["executed_at"], "executed_at") <= cutoff
        )
        settlements = tuple(
            row
            for row in settlements
            if _timestamp(row["settled_at"], "settled_at") <= cutoff
        )
    execution_by_id = {row["execution_id"]: row for row in executions}
    selected = []
    for execution in executions:
        normalized_funding = execution_funding_type(execution)
        if game_id is not None and execution["game_id"] != game_id:
            continue
        if week is not None and _week(execution["game_id"]) != week:
            continue
        if funding_type is not None and normalized_funding != funding_type:
            continue
        selected.append(execution)
    selected_by_id = {row["execution_id"]: row for row in selected}
    currencies = {row["currency"] for row in selected}
    if len(currencies) > 1:
        raise PerformanceAccountingError(
            "performance accounting cannot combine multiple currencies"
        )
    settlement_by_execution = {
        row["execution_id"]: row
        for row in settlements
        if row["execution_id"] in selected_by_id
    }
    for execution_id, settlement in settlement_by_execution.items():
        if settlement["execution"] != selected_by_id[execution_id]:
            raise PerformanceAccountingError("settlement execution provenance mismatch")
    entries = []
    for execution in selected:
        settlement = settlement_by_execution.get(execution["execution_id"])
        normalized_funding = execution_funding_type(execution)
        entries.append(
            {
                "execution_id": execution["execution_id"],
                "game_id": execution["game_id"],
                "week": _week(execution["game_id"]),
                "executed_at": execution["executed_at"],
                "funding_type": normalized_funding,
                "side": execution["side"],
                "source_book": execution["source_book"],
                "american_odds": execution["american_odds"],
                "stake_or_face_value": execution["stake"],
                "currency": execution["currency"],
                "related_observation_id": execution["related_observation_id"],
                "status": (
                    "EXECUTED_AND_SETTLED"
                    if settlement is not None
                    else "EXECUTED_AWAITING_RESULT"
                ),
                "settlement_id": None if settlement is None else settlement["settlement_id"],
                "final_result_id": None if settlement is None else settlement["final_result_id"],
                "closing_observation_id": (
                    None if settlement is None else settlement["closing_observation_id"]
                ),
                "outcome": None if settlement is None else settlement["outcome"],
                "realized_cash_change": (
                    None if settlement is None else settlement["net_profit"]
                ),
                "draftkings_clv_probability": (
                    None if settlement is None else settlement["draftkings_clv_probability"]
                ),
                "consensus_clv_probability": (
                    None if settlement is None else settlement["consensus_clv_probability"]
                ),
                "clv_available": (
                    settlement is not None
                    and settlement["draftkings_clv_probability"] is not None
                    and settlement["consensus_clv_probability"] is not None
                ),
            }
        )
    settled_entries = [entry for entry in entries if entry["status"] == "EXECUTED_AND_SETTLED"]
    cash_entries = [entry for entry in entries if entry["funding_type"] == "CASH"]
    settled_cash = [entry for entry in settled_entries if entry["funding_type"] == "CASH"]
    bonus_entries = [entry for entry in entries if entry["funding_type"] == "BONUS_BET"]
    settled_bonus = [entry for entry in settled_entries if entry["funding_type"] == "BONUS_BET"]
    cash_staked = sum(float(entry["stake_or_face_value"]) for entry in settled_cash)
    cash_profit = sum(float(entry["realized_cash_change"]) for entry in settled_cash)
    bonus_face = sum(float(entry["stake_or_face_value"]) for entry in settled_bonus)
    bonus_proceeds = sum(float(entry["realized_cash_change"]) for entry in settled_bonus)
    dk_clv = [float(entry["draftkings_clv_probability"]) for entry in settled_entries if entry["draftkings_clv_probability"] is not None]
    consensus_clv = [float(entry["consensus_clv_probability"]) for entry in settled_entries if entry["consensus_clv_probability"] is not None]
    clv_available = [entry for entry in settled_entries if entry["clv_available"]]
    caller_supplied = None
    if starting_cash is not None or starting_bonus is not None:
        executed_bonus_face = sum(float(entry["stake_or_face_value"]) for entry in bonus_entries)
        if starting_bonus is not None and executed_bonus_face > starting_bonus:
            raise PerformanceAccountingError(
                "recorded bonus executions exceed caller-supplied bonus inventory"
            )
        caller_supplied = {
            "classification": "CALLER_SUPPLIED",
            "starting_cash": starting_cash,
            "starting_bonus": starting_bonus,
            "cash_after_recorded_activity": (
                None if starting_cash is None else starting_cash + cash_profit + bonus_proceeds
            ),
            "bonus_inventory_after_recorded_executions": (
                None if starting_bonus is None else starting_bonus - executed_bonus_face
            ),
        }
    return {
        "classification": CLASSIFICATION,
        "read_only": True,
        "non_prospective": True,
        "filters": {
            "through": None if cutoff is None else cutoff.isoformat().replace("+00:00", "Z"),
            "game_id": game_id,
            "week": week,
            "funding_type": funding_type,
        },
        "execution_count": len(entries),
        "settled_execution_count": len(settled_entries),
        "unsettled_execution_count": len(entries) - len(settled_entries),
        "unmatched_settlement_count": sum(
            row["execution_id"] not in execution_by_id for row in settlements
        ),
        "currency": next(iter(currencies), None),
        "cash": {
            "execution_count": len(cash_entries),
            "settled_count": len(settled_cash),
            "wins": sum(entry["outcome"] == "WIN" for entry in settled_cash),
            "losses": sum(entry["outcome"] == "LOSS" for entry in settled_cash),
            "pushes": sum(entry["outcome"] == "PUSH" for entry in settled_cash),
            "total_cash_staked": cash_staked,
            "net_cash_profit": cash_profit,
            "cash_roi": None if cash_staked == 0 else cash_profit / cash_staked,
            "average_execution_break_even_probability": _mean(
                [
                    float(settlement_by_execution[entry["execution_id"]]["execution_break_even_probability"])
                    for entry in cash_entries
                    if entry["execution_id"] in settlement_by_execution
                ]
            ),
            "average_model_edge_at_execution": None,
        },
        "bonus_bet": {
            "execution_count": len(bonus_entries),
            "settled_count": len(settled_bonus),
            "wins": sum(entry["outcome"] == "WIN" for entry in settled_bonus),
            "losses": sum(entry["outcome"] == "LOSS" for entry in settled_bonus),
            "bonus_face_value_executed": sum(
                float(entry["stake_or_face_value"]) for entry in bonus_entries
            ),
            "settled_bonus_face_value": bonus_face,
            "bonus_cash_proceeds": bonus_proceeds,
            "conversion_rate": None if bonus_face == 0 else bonus_proceeds / bonus_face,
        },
        "combined": {
            "cash_wager_net_profit": cash_profit,
            "bonus_bet_cash_proceeds": bonus_proceeds,
            "total_realized_cash_change": cash_profit + bonus_proceeds,
        },
        "clv": {
            "average_draftkings_clv_probability": _mean(dk_clv),
            "average_consensus_clv_probability": _mean(consensus_clv),
            "positive_count": sum(entry["draftkings_clv_probability"] > 0 for entry in clv_available),
            "negative_count": sum(entry["draftkings_clv_probability"] < 0 for entry in clv_available),
            "zero_count": sum(entry["draftkings_clv_probability"] == 0 for entry in clv_available),
            "available_count": len(clv_available),
            "unavailable_count": len(settled_entries) - len(clv_available),
            "positive_rate": (
                None
                if not clv_available
                else sum(entry["draftkings_clv_probability"] > 0 for entry in clv_available)
                / len(clv_available)
            ),
            "negative_rate": (
                None
                if not clv_available
                else sum(entry["draftkings_clv_probability"] < 0 for entry in clv_available)
                / len(clv_available)
            ),
        },
        "caller_supplied": caller_supplied,
        "executions": entries,
    }
