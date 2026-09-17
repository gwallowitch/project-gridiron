from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from gridiron.market.closing_settlement import (
    ClosingSettlementError,
    append_execution,
    append_settlement,
    build_closing_line,
    build_execution,
    build_final_result,
    build_settlement,
    read_executions,
    read_settlements,
)
from gridiron.market.moneyline import remove_two_sided_vig
from gridiron.market.operational_history import canonical_json
from gridiron.market.performance import (
    PerformanceAccountingError,
    build_performance_report,
    execution_funding_type,
)
from scripts import gridiron_performance

GAME = "2026_01_NE_SEA"
KICKOFF = "2026-09-10T00:20:00Z"


def execution(
    *, funding_type=None, odds=-110, stake=10.0, side="HOME", executed_at="2026-09-09T23:00:00Z"
):
    return build_execution(
        game_id=GAME,
        kickoff_at=KICKOFF,
        executed_at=executed_at,
        side=side,
        american_odds=odds,
        stake=stake,
        currency="USD",
        source_book="DraftKings",
        related_observation_id="a" * 64,
        funding_type=funding_type,
    )


def result(home=24, away=17):
    return build_final_result(
        game_id=GAME,
        status="FINAL",
        home_score=home,
        away_score=away,
        source="retained official fixture",
        acquired_at="2026-09-10T04:00:00Z",
    )


def close(dk_home=-130, dk_away=110):
    fair = remove_two_sided_vig(dk_home, dk_away)
    return build_closing_line(
        {
            "observation_id": "b" * 64,
            "provider": "the-odds-api-operational-step91q:NEAR_KICKOFF",
            "game": {"game_id": GAME, "kickoff_at": KICKOFF},
            "timing": {"collected_at": "2026-09-10T00:10:00Z"},
            "market": {
                "home_probability": fair.home_fair_probability,
                "away_probability": fair.away_fair_probability,
            },
            "books": [
                {"book": book, "home_odds": dk_home, "away_odds": dk_away}
                for book in ("BetMGM", "FanDuel", "DraftKings")
            ],
        }
    )


def settlement(execution_row, result_row=None, close_row=None):
    return build_settlement(
        execution_row,
        result() if result_row is None else result_row,
        closing_line=close() if close_row is None else close_row,
        settled_at="2026-09-10T04:01:00Z",
    )


def ledgers(tmp_path: Path):
    return tmp_path / "executions.jsonl", tmp_path / "settlements.jsonl"


def append_pair(execution_path, settlement_path, execution_row, **kwargs):
    append_execution(execution_path, execution_row)
    row = settlement(execution_row, **kwargs)
    append_settlement(settlement_path, row)
    return row


def test_legacy_execution_remains_schema1_cash_and_round_trips(tmp_path: Path) -> None:
    row = execution()
    assert row["schema_version"] == 1
    assert "funding_type" not in row
    assert execution_funding_type(row) == "CASH"
    path = tmp_path / "executions.jsonl"
    append_execution(path, row)
    assert read_executions(path) == (row,)


def test_explicit_cash_and_bonus_are_schema2_and_identity_bound() -> None:
    cash = execution(funding_type="CASH")
    bonus = execution(funding_type="BONUS_BET")
    assert cash["schema_version"] == bonus["schema_version"] == 2
    assert cash["funding_type"] == "CASH"
    assert bonus["funding_type"] == "BONUS_BET"
    assert cash["execution_id"] != bonus["execution_id"]


@pytest.mark.parametrize("funding_type", ["FREE_BET", "", "cash", 1])
def test_unknown_funding_type_rejected(funding_type) -> None:
    with pytest.raises(ClosingSettlementError, match="funding_type"):
        execution(funding_type=funding_type)


def test_persisted_funding_type_cannot_mutate(tmp_path: Path) -> None:
    row = execution(funding_type="BONUS_BET")
    row["funding_type"] = "CASH"
    path = tmp_path / "executions.jsonl"
    path.write_text(canonical_json(row) + "\n", encoding="utf-8")
    with pytest.raises(ClosingSettlementError, match="execution_id"):
        read_executions(path)


@pytest.mark.parametrize(
    "odds,home,away,expected",
    [(200, 24, 17, 20.0), (-110, 24, 17, 1000 / 110), (200, 17, 24, -10.0)],
)
def test_cash_economics_preserved(odds, home, away, expected) -> None:
    row = settlement(execution(funding_type="CASH", odds=odds), result(home, away))
    assert row["net_profit"] == pytest.approx(expected)
    assert row["cash_staked"] == 10.0
    assert row["bonus_face_value_consumed"] == 0.0


def test_cash_push_is_zero() -> None:
    row = settlement(execution(funding_type="CASH"), result(20, 20))
    assert row["outcome"] == "PUSH" and row["net_profit"] == 0.0


@pytest.mark.parametrize(
    "odds,home,away,expected,conversion",
    [
        (200, 24, 17, 20.0, 2.0),
        (-110, 24, 17, 1000 / 110, 100 / 110),
        (200, 17, 24, 0.0, 0.0),
    ],
)
def test_bonus_bet_economics(odds, home, away, expected, conversion) -> None:
    row = settlement(
        execution(funding_type="BONUS_BET", odds=odds), result(home, away)
    )
    assert row["net_profit"] == pytest.approx(expected)
    assert row["realized_cash_change"] == pytest.approx(expected)
    assert row["cash_staked"] == 0.0
    assert row["bonus_face_value_consumed"] == 10.0
    assert row["bonus_cash_proceeds"] == pytest.approx(expected)
    assert row["bonus_conversion_rate"] == pytest.approx(conversion)


def test_bonus_bet_push_fails_closed() -> None:
    with pytest.raises(ClosingSettlementError, match="reissue"):
        settlement(execution(funding_type="BONUS_BET"), result(20, 20))


def test_schema2_settlement_round_trip_and_tamper_detection(tmp_path: Path) -> None:
    path = tmp_path / "settlements.jsonl"
    row = settlement(execution(funding_type="BONUS_BET", odds=200))
    append_settlement(path, row)
    assert read_settlements(path) == (row,)
    bad = deepcopy(row)
    bad["bonus_cash_proceeds"] = 999.0
    path.write_text(canonical_json(bad) + "\n", encoding="utf-8")
    with pytest.raises(ClosingSettlementError):
        read_settlements(path)


def test_cash_roi_excludes_bonus_and_combined_cash_is_separate(tmp_path: Path) -> None:
    executions, settlements = ledgers(tmp_path)
    append_pair(executions, settlements, execution(funding_type="CASH", odds=200))
    append_pair(
        executions,
        settlements,
        execution(
            funding_type="BONUS_BET", odds=200, executed_at="2026-09-09T23:01:00Z"
        ),
    )
    report = build_performance_report(executions, settlements)
    assert report["cash"]["total_cash_staked"] == 10.0
    assert report["cash"]["net_cash_profit"] == 20.0
    assert report["cash"]["cash_roi"] == 2.0
    assert report["bonus_bet"]["bonus_cash_proceeds"] == 20.0
    assert report["bonus_bet"]["conversion_rate"] == 2.0
    assert report["combined"]["total_realized_cash_change"] == 40.0


def test_bonus_loss_is_zero_cash_not_negative_loss(tmp_path: Path) -> None:
    executions, settlements = ledgers(tmp_path)
    append_pair(
        executions,
        settlements,
        execution(funding_type="BONUS_BET"),
        result_row=result(17, 24),
    )
    report = build_performance_report(executions, settlements)
    assert report["bonus_bet"]["losses"] == 1
    assert report["bonus_bet"]["bonus_cash_proceeds"] == 0.0
    assert report["combined"]["total_realized_cash_change"] == 0.0


def test_unsettled_execution_is_not_a_loss(tmp_path: Path) -> None:
    executions, settlements = ledgers(tmp_path)
    append_execution(executions, execution(funding_type="CASH"))
    report = build_performance_report(executions, settlements)
    assert report["unsettled_execution_count"] == 1
    assert report["cash"]["losses"] == 0
    assert report["executions"][0]["status"] == "EXECUTED_AWAITING_RESULT"


def test_recommendation_and_result_without_execution_are_absent(tmp_path: Path) -> None:
    executions, settlements = ledgers(tmp_path)
    recommendation = {"is_bet": True}
    orphan = settlement(execution(funding_type="CASH"))
    append_settlement(settlements, orphan)
    report = build_performance_report(executions, settlements)
    assert recommendation["is_bet"] is True
    assert report["execution_count"] == 0
    assert report["unmatched_settlement_count"] == 1


def test_clv_values_and_counts_are_preserved(tmp_path: Path) -> None:
    executions, settlements = ledgers(tmp_path)
    first = execution(funding_type="CASH", odds=-110)
    second = execution(
        funding_type="BONUS_BET", odds=-150, executed_at="2026-09-09T23:01:00Z"
    )
    one = append_pair(executions, settlements, first)
    two = append_pair(executions, settlements, second)
    report = build_performance_report(executions, settlements)
    assert report["clv"]["positive_count"] == 1
    assert report["clv"]["negative_count"] == 1
    assert report["clv"]["average_draftkings_clv_probability"] == pytest.approx(
        (one["draftkings_clv_probability"] + two["draftkings_clv_probability"]) / 2
    )
    assert report["clv"]["average_consensus_clv_probability"] == pytest.approx(
        (one["consensus_clv_probability"] + two["consensus_clv_probability"]) / 2
    )


def test_clv_unavailable_remains_explicit(tmp_path: Path) -> None:
    executions, settlements = ledgers(tmp_path)
    row = execution(funding_type="CASH")
    append_execution(executions, row)
    append_settlement(
        settlements,
        build_settlement(
            row,
            result(),
            closing_line=None,
            settled_at="2026-09-10T04:01:00Z",
        ),
    )
    report = build_performance_report(executions, settlements)
    assert report["clv"]["available_count"] == 0
    assert report["clv"]["unavailable_count"] == 1
    assert report["executions"][0]["clv_available"] is False


def test_funding_week_game_and_through_filters(tmp_path: Path) -> None:
    executions, settlements = ledgers(tmp_path)
    cash = execution(funding_type="CASH")
    bonus = execution(
        funding_type="BONUS_BET", executed_at="2026-09-09T23:01:00Z"
    )
    append_execution(executions, cash)
    append_execution(executions, bonus)
    assert build_performance_report(executions, settlements, funding_type="CASH")[
        "execution_count"
    ] == 1
    assert build_performance_report(executions, settlements, week=1)[
        "execution_count"
    ] == 2
    assert build_performance_report(executions, settlements, game_id=GAME)[
        "execution_count"
    ] == 2
    before_second = datetime(2026, 9, 9, 23, 0, 30, tzinfo=UTC)
    assert build_performance_report(executions, settlements, through=before_second)[
        "execution_count"
    ] == 1


@pytest.mark.parametrize("ledger", ["executions", "settlements"])
def test_malformed_ledgers_fail_closed(tmp_path: Path, ledger: str) -> None:
    executions, settlements = ledgers(tmp_path)
    target = executions if ledger == "executions" else settlements
    target.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(PerformanceAccountingError):
        build_performance_report(executions, settlements)


def test_duplicate_execution_semantics_remain_append_only(tmp_path: Path) -> None:
    executions, _ = ledgers(tmp_path)
    row = execution(funding_type="CASH")
    append_execution(executions, row)
    before = executions.read_bytes()
    with pytest.raises(ClosingSettlementError, match="duplicate"):
        append_execution(executions, row)
    assert executions.read_bytes() == before


def test_report_is_read_only_and_caller_baselines_are_not_persisted(tmp_path: Path) -> None:
    executions, settlements = ledgers(tmp_path)
    append_pair(executions, settlements, execution(funding_type="BONUS_BET"))
    before = executions.read_bytes(), settlements.read_bytes()
    report = build_performance_report(
        executions, settlements, starting_cash=38.0, starting_bonus=90.0
    )
    assert report["caller_supplied"]["classification"] == "CALLER_SUPPLIED"
    assert (executions.read_bytes(), settlements.read_bytes()) == before


def test_cli_json_is_deterministic_and_creates_no_files(tmp_path: Path, capsys) -> None:
    executions, settlements = ledgers(tmp_path)
    args = [
        "summary",
        "--executions",
        str(executions),
        "--settlements",
        str(settlements),
        "--json",
    ]
    assert gridiron_performance.main(args) == 0
    first = capsys.readouterr().out
    assert gridiron_performance.main(args) == 0
    second = capsys.readouterr().out
    assert first == second
    assert json.loads(first)["execution_count"] == 0
    assert not executions.exists() and not settlements.exists()


def test_invalid_caller_inputs_fail_closed(tmp_path: Path) -> None:
    executions, settlements = ledgers(tmp_path)
    with pytest.raises(PerformanceAccountingError):
        build_performance_report(executions, settlements, starting_cash=-1)
    with pytest.raises(PerformanceAccountingError):
        build_performance_report(executions, settlements, funding_type="OTHER")
