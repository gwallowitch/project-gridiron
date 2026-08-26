from __future__ import annotations

import json
from pathlib import Path

import pytest

from gridiron.market.prospective_ledger import (
    CONSENSUS_BOOKS,
    LedgerError,
    append_event,
    build_decision,
    build_settlement,
    capture_decision,
    implied_probability,
    ledger_summary,
    read_ledger,
    settle_decision,
    validate_events,
    validate_ledger,
)


def _payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "game_id": "2026_01_BUF_NYJ",
        "season": 2026,
        "season_type": "REG",
        "week": 1,
        "kickoff_at": "2026-09-13T17:00:00Z",
        "decision_at": "2026-09-13T14:00:00Z",
        "home_team": "NYJ",
        "away_team": "BUF",
        "def_epa": None,
        "market_observations": [
            {
                "book": book,
                "home_odds": 120,
                "away_odds": -140,
                "observed_at": "2026-09-13T13:55:00Z",
            }
            for book in CONSENSUS_BOOKS
        ],
    }
    payload.update(updates)
    return payload


def test_decision_is_deterministic_and_week_one_def_epa_is_zero() -> None:
    first = build_decision(_payload())
    second = build_decision(_payload())

    assert first == second
    assert first["event_type"] == "DECISION"
    assert first["def_epa"] == 0.0
    assert len(first["event_id"]) == 64
    assert len(first["observation_id"]) == 64


@pytest.mark.parametrize("week", [2, 8, 16])
def test_missing_later_week_def_epa_is_rejected(week: int) -> None:
    with pytest.raises(LedgerError, match="later-week DEF EPA"):
        build_decision(_payload(week=week))


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"season": 2025}, "2026 regular season"),
        ({"season_type": "POST"}, "2026 regular season"),
        ({"week": 17}, "Weeks 1-16"),
        ({"decision_at": "2026-09-13T17:00:00Z"}, "pre-kickoff"),
    ],
)
def test_frozen_window_and_timing_are_enforced(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(LedgerError, match=message):
        build_decision(_payload(**updates))


def test_seven_complete_market_observations_are_required() -> None:
    observations = _payload()["market_observations"]
    assert isinstance(observations, list)
    with pytest.raises(LedgerError, match="seven complete"):
        build_decision(_payload(market_observations=observations[:-1]))


def test_missing_selected_execution_price_is_retained_as_non_bet() -> None:
    decision = build_decision(
        _payload(
            execution_prices={
                "book": "DraftKings",
                "home_odds": None,
                "away_odds": None,
            }
        )
    )

    assert decision["is_bet"] is False
    assert decision["selected_execution_odds"] is None
    assert decision["break_even_probability"] is None
    assert decision["edge"] is None


def test_strictly_positive_edge_excludes_zero() -> None:
    initial = build_decision(_payload())
    selected = initial["selected_side"]
    candidate = initial["candidate_home_probability"]
    side_probability = candidate if selected == "HOME" else 1.0 - candidate
    odds = round(100 * (1 - side_probability) / side_probability)
    odds = max(100, odds)
    execution = {
        "book": "DraftKings",
        "home_odds": odds if selected == "HOME" else -110,
        "away_odds": odds if selected == "AWAY" else -110,
    }
    decision = build_decision(_payload(execution_prices=execution))

    assert decision["is_bet"] == (decision["edge"] > 0.0)


@pytest.mark.parametrize(
    ("odds", "expected"),
    [(-200, 2 / 3), (150, 0.4)],
)
def test_american_odds_probability(odds: int, expected: float) -> None:
    assert implied_probability(odds) == pytest.approx(expected)


def test_duplicate_decision_is_rejected() -> None:
    decision = build_decision(_payload())
    with pytest.raises(LedgerError, match="duplicate decision"):
        validate_events((decision, decision | {"event_id": "f" * 64}))


def test_orphan_duplicate_and_inconsistent_settlements_are_rejected() -> None:
    decision = build_decision(_payload())
    settlement = build_settlement(
        decision, result="HOME", settled_at="2026-09-13T21:00:00Z"
    )
    with pytest.raises(LedgerError, match="orphan settlement"):
        validate_events((settlement,))
    with pytest.raises(LedgerError, match="duplicate settlement"):
        validate_events((decision, settlement, settlement | {"event_id": "e" * 64}))
    with pytest.raises(LedgerError, match="inconsistent settlement"):
        validate_events((decision, settlement | {"profit_units": 99.0}))


def test_settlement_uses_captured_odds_for_wins_and_one_unit_for_losses() -> None:
    decision = build_decision(
        _payload(
            execution_prices={
                "book": "DraftKings",
                "home_odds": 150,
                "away_odds": 150,
            }
        )
    )
    win = build_settlement(
        decision,
        result=decision["selected_side"],
        settled_at="2026-09-13T21:00:00Z",
    )
    losing_side = "AWAY" if decision["selected_side"] == "HOME" else "HOME"
    loss = build_settlement(
        decision, result=losing_side, settled_at="2026-09-13T21:00:00Z"
    )

    assert win["profit_units"] == 1.5
    assert loss["profit_units"] == -1.0


def test_non_bet_settlement_is_zero() -> None:
    decision = build_decision(
        _payload(
            execution_prices={
                "book": "DraftKings",
                "home_odds": None,
                "away_odds": None,
            }
        )
    )
    settlement = build_settlement(
        decision, result="HOME", settled_at="2026-09-13T21:00:00Z"
    )
    assert settlement["profit_units"] == 0.0


def test_append_only_round_trip_and_unsettled_bet_not_loss(tmp_path: Path) -> None:
    ledger = tmp_path / "prospective.jsonl"
    decision = capture_decision(
        ledger,
        _payload(
            execution_prices={
                "book": "DraftKings",
                "home_odds": 300,
                "away_odds": 300,
            }
        ),
    )

    summary = ledger_summary(ledger)
    assert decision["is_bet"] is True
    assert summary["unsettled_bets"] == 1
    assert summary["profit_units"] == 0

    settlement = settle_decision(
        ledger,
        game_id=decision["game_id"],
        result=decision["selected_side"],
        settled_at="2026-09-13T21:00:00Z",
    )
    assert len(read_ledger(ledger)) == 2
    assert validate_ledger(ledger).settlements[decision["game_id"]] == settlement
    assert ledger_summary(ledger)["profit_units"] == 3.0


def test_canonical_json_lines_and_corruption_detection(tmp_path: Path) -> None:
    ledger = tmp_path / "prospective.jsonl"
    decision = build_decision(_payload())
    append_event(ledger, decision)
    assert json.loads(ledger.read_text(encoding="utf-8")) == decision

    ledger.write_text(ledger.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(LedgerError, match="blank ledger line"):
        validate_ledger(ledger)
