from __future__ import annotations

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

GAME = "2026_01_NE_SEA"
KICKOFF = "2026-09-10T00:20:00Z"


def execution(side="HOME", odds=-110, stake=10.0):
    return build_execution(game_id=GAME, kickoff_at=KICKOFF, executed_at="2026-09-09T23:00:00Z", side=side, american_odds=odds, stake=stake, currency="USD", source_book="DraftKings", related_observation_id="a" * 64)


def result(home=24, away=17, status="FINAL"):
    return build_final_result(game_id=GAME, status=status, home_score=home, away_score=away, source="retained official final fixture", acquired_at="2026-09-10T04:00:00Z")


def close(dk_home=-130, dk_away=110):
    fair = remove_two_sided_vig(dk_home, dk_away)
    return build_closing_line({
        "observation_id": "b" * 64,
        "provider": "the-odds-api-operational-step91q:NEAR_KICKOFF",
        "game": {"game_id": GAME, "kickoff_at": KICKOFF},
        "timing": {"collected_at": "2026-09-10T00:10:00Z"},
        "market": {"home_probability": fair.home_fair_probability, "away_probability": fair.away_fair_probability},
        "books": [
            {"book": "BetMGM", "home_odds": dk_home, "away_odds": dk_away},
            {"book": "FanDuel", "home_odds": dk_home, "away_odds": dk_away},
            {"book": "DraftKings", "home_odds": dk_home, "away_odds": dk_away},
        ],
    })


def settlement(execution_row=None, result_row=None, close_row=None):
    return build_settlement(execution_row or execution(), result_row or result(), closing_line=close() if close_row is None else close_row, settled_at="2026-09-10T04:01:00Z")


def test_valid_explicit_execution_roundtrip_and_duplicate(tmp_path) -> None:
    path = tmp_path / "executions.jsonl"
    row = execution()
    append_execution(path, row)
    assert read_executions(path) == (row,)
    with pytest.raises(ClosingSettlementError, match="duplicate"):
        append_execution(path, row)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"side": "DRAW"}, {"stake": 0.0}, {"stake": -1.0},
        {"american_odds": 50}, {"executed_at": KICKOFF},
        {"executed_at": "2026-09-10T00:21:00Z"},
        {"game_id": "not-canonical"}, {"related_observation_id": "short"},
    ],
)
def test_invalid_execution_rejected(kwargs) -> None:
    base = {"game_id": GAME, "kickoff_at": KICKOFF, "executed_at": "2026-09-09T23:00:00Z", "side": "HOME", "american_odds": -110, "stake": 10.0, "currency": "USD", "source_book": "DraftKings"}
    with pytest.raises(ClosingSettlementError):
        build_execution(**(base | kwargs))


def test_hash_valid_but_semantically_invalid_execution_rejected(tmp_path) -> None:
    row = execution()
    row["side"] = "DRAW"
    material = dict(row)
    material.pop("execution_id")
    import hashlib
    row["execution_id"] = hashlib.sha256(canonical_json(material).encode()).hexdigest()
    path = tmp_path / "executions.jsonl"
    path.write_text(canonical_json(row) + "\n", encoding="utf-8")
    with pytest.raises(ClosingSettlementError):
        read_executions(path)


@pytest.mark.parametrize(
    ("side", "home", "away", "outcome"),
    [("HOME", 24, 17, "WIN"), ("HOME", 17, 24, "LOSS"), ("AWAY", 17, 24, "WIN"), ("AWAY", 24, 17, "LOSS"), ("HOME", 20, 20, "PUSH")],
)
def test_home_away_and_tie_settlement(side, home, away, outcome) -> None:
    row = settlement(execution(side=side), result(home, away))
    assert row["outcome"] == outcome


def test_positive_and_negative_payout_math() -> None:
    assert settlement(execution(odds=150, stake=10))["net_profit"] == pytest.approx(15.0)
    assert settlement(execution(odds=-200, stake=10))["net_profit"] == pytest.approx(5.0)
    assert settlement(execution(side="AWAY", odds=150, stake=10))["net_profit"] == -10.0


def test_nonfinal_result_does_not_settle() -> None:
    with pytest.raises(ClosingSettlementError, match="FINAL"):
        result(status="IN_PROGRESS")


@pytest.mark.parametrize(
    ("execution_odds", "close_odds", "positive"),
    [(-110, -130, True), (-150, -130, False), (150, 130, True), (110, 130, False)],
)
def test_favorite_and_underdog_dk_clv_orientation(execution_odds, close_odds, positive) -> None:
    if execution_odds < 0:
        row = settlement(execution(odds=execution_odds), close_row=close(close_odds, 110))
    else:
        row = settlement(execution(side="AWAY", odds=execution_odds), result_row=result(17, 24), close_row=close(-130, close_odds))
    assert (row["draftkings_clv_probability"] > 0) is positive
    assert (row["consensus_clv_probability"] > 0) is positive


def test_same_price_zero_same_side_and_consensus_orientation() -> None:
    row = settlement(execution(side="AWAY", odds=130), result_row=result(17, 24), close_row=close(-150, 130))
    assert row["closing_draftkings_odds_same_side"] == 130
    assert row["draftkings_clv_probability"] == pytest.approx(0.0)
    assert row["consensus_clv_probability"] == pytest.approx(
        row["closing_consensus_probability_same_side"]
        - row["execution_break_even_probability"]
    )
    assert row["consensus_clv_probability"] < 0.0


def test_no_close_settles_without_fabricated_clv() -> None:
    row = build_settlement(execution(), result(), closing_line=None, settled_at="2026-09-10T04:01:00Z")
    assert row["outcome"] == "WIN"
    assert row["closing_observation_id"] is None
    assert row["draftkings_clv_probability"] is None
    assert row["consensus_clv_probability"] is None


def test_settlement_append_only_and_contradiction_rejected(tmp_path) -> None:
    path = tmp_path / "settlements.jsonl"
    first = settlement()
    append_settlement(path, first)
    before = path.read_bytes()
    with pytest.raises(ClosingSettlementError, match="already settled"):
        append_settlement(path, settlement(result_row=result(27, 17)))
    assert path.read_bytes() == before
    assert read_settlements(path) == (first,)


def test_self_hashed_semantically_invalid_settlement_rejected(tmp_path) -> None:
    import hashlib

    row = settlement()
    row["net_profit"] = 999.0
    material = dict(row)
    material.pop("settlement_id")
    row["settlement_id"] = hashlib.sha256(canonical_json(material).encode()).hexdigest()
    path = tmp_path / "settlements.jsonl"
    path.write_text(canonical_json(row) + "\n", encoding="utf-8")
    with pytest.raises(ClosingSettlementError, match="semantics"):
        read_settlements(path)


def test_recommendation_object_never_creates_execution(tmp_path) -> None:
    recommendation = {"is_bet": True, "selected_side": "HOME"}
    path = tmp_path / "executions.jsonl"
    assert recommendation["is_bet"] is True
    assert read_executions(path) == () and not path.exists()
