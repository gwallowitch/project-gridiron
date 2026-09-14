from __future__ import annotations

from copy import deepcopy

import pytest

from gridiron.market.closing_settlement import (
    ClosingSettlementError,
    build_closing_line,
    select_closing_observation,
)
from gridiron.market.operational_history import (
    OperationalHistoryError,
    append_operational_observation,
    read_operational_history,
)
from scripts.gridiron_operational_prediction import build_operational_prediction


def prediction(captured: str, *, provider="the-odds-api-operational-step91q:T1H", shift=0):
    return build_operational_prediction(
        {
            "schema_version": 1,
            "provider": provider,
            "captured_at": captured,
            "game": {"game_id": "2026_01_NE_SEA", "season": 2026, "week": 1, "season_type": "REG", "home_team": "SEA", "away_team": "NE", "kickoff_at": "2026-09-10T00:20:00Z"},
            "offers": [
                {"book": book, "home_odds": -175 - index - shift, "away_odds": 145 + index + shift, "observed_at": captured}
                for index, book in enumerate(("BetMGM", "FanDuel", "DraftKings"))
            ],
        },
        def_epa=0.0,
        def_epa_source="frozen Week 1 neutral rule",
    )


def test_latest_actual_timestamp_wins_not_target_label(tmp_path) -> None:
    path = tmp_path / "history.jsonl"
    early = append_operational_observation(path, prediction("2026-09-09T23:20:00Z", provider="the-odds-api-operational-step91q:NEAR_KICKOFF"))
    late = append_operational_observation(path, prediction("2026-09-10T00:00:00Z", provider="manual-game-day-entry", shift=2))
    selected = select_closing_observation(read_operational_history(path), "2026_01_NE_SEA")
    assert selected == late and selected != early
    close = build_closing_line(selected)
    assert close["closing_observation_id"] == late["observation_id"]
    assert close["classification"] == "NON_PROSPECTIVE_CLOSING_LINE_OBSERVATION"
    assert close["minutes_before_kickoff"] == pytest.approx(20.0)


def test_no_eligible_or_postkickoff_observation_is_unavailable() -> None:
    row = {"game": {"game_id": "g", "kickoff_at": "2026-09-10T00:20:00Z"}, "timing": {"collected_at": "2026-09-10T00:20:00Z"}}
    assert select_closing_observation([row], "g") is None
    assert select_closing_observation([], "g") is None


def test_contradictory_latest_timestamp_fails_closed(tmp_path) -> None:
    path = tmp_path / "history.jsonl"
    append_operational_observation(path, prediction("2026-09-10T00:00:00Z"))
    append_operational_observation(path, prediction("2026-09-10T00:00:00Z", shift=5))
    with pytest.raises(ClosingSettlementError, match="contradictory"):
        select_closing_observation(read_operational_history(path), "2026_01_NE_SEA")


def test_malformed_history_fails_through_hardened_reader(tmp_path) -> None:
    path = tmp_path / "history.jsonl"
    row = append_operational_observation(path, prediction("2026-09-10T00:00:00Z"))
    bad = deepcopy(row)
    bad["provider"] = "tampered"
    path.write_text(str(bad), encoding="utf-8")
    with pytest.raises(OperationalHistoryError):
        read_operational_history(path)
