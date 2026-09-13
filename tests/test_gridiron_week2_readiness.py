from __future__ import annotations

import json

import polars as pl
import pytest

from scripts import gridiron_week2_readiness as readiness
from scripts.gridiron_operational_prediction import DEF_EPA_COEFFICIENT

GAME = {"game_id": "2026_02_NE_SEA", "season": 2026, "week": 2, "season_type": "REG", "home_team": "SEA", "away_team": "NE", "kickoff_at": "2026-09-20T17:00:00Z"}


def schedule(tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps([GAME]), encoding="utf-8")
    return path


def pbp(*, home=True, away=True, extras=False):
    rows = []
    if home:
        rows.append(("w1", 2026, 1, "NE", "SEA", "pass", 0.3))
    if away:
        rows.append(("w1", 2026, 1, "SEA", "NE", "run", -0.2))
    if extras:
        rows.extend([("old", 2025, 18, "NE", "SEA", "pass", 999.0), ("current", 2026, 2, "NE", "SEA", "pass", 999.0), ("future", 2026, 3, "SEA", "NE", "pass", -999.0)])
    return pl.DataFrame(rows, schema=["game_id", "season", "week", "posteam", "defteam", "play_type", "epa"], orient="row")


def test_valid_week1_data_produces_computed_zero(tmp_path) -> None:
    row = readiness.audit_week2(schedule(tmp_path), pbp_loader=lambda _season: pbp(extras=True))[0]
    assert row["week1_home_def_epa_available"] is True
    assert row["week1_away_def_epa_available"] is True
    assert row["def_epa_input_status"] == "READY"
    assert row["home_def_epa_improvement"] == pytest.approx(0.0)
    assert row["away_def_epa_improvement"] == pytest.approx(0.0)
    assert row["def_epa_trend_advantage"] == pytest.approx(0.0)
    assert row["reason"] == "COMPUTED_ZERO_FROM_VALID_WEEK1_DATA"
    assert "computed" in row["provenance"] and "neutral fallback" not in row["provenance"]


@pytest.mark.parametrize(("home", "away", "reason"), [(False, True, "HOME_WEEK1_DEF_EPA_MISSING"), (True, False, "AWAY_WEEK1_DEF_EPA_MISSING")])
def test_missing_team_week1_data_is_not_ready(tmp_path, home, away, reason) -> None:
    row = readiness.audit_week2(schedule(tmp_path), pbp_loader=lambda _season: pbp(home=home, away=away))[0]
    assert row["def_epa_input_status"] == "NOT_READY"
    assert row["reason"] == reason


def test_prior_week_missing_fails_closed_despite_other_seasons_and_weeks(tmp_path) -> None:
    with pytest.raises(readiness.Week2ReadinessError, match="Week 1"):
        readiness.audit_week2(schedule(tmp_path), pbp_loader=lambda _season: pbp(home=False, away=False, extras=True))


def test_cache_clear_precedes_current_season_load(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(readiness.nfl, "clear_cache", lambda key: calls.append(("clear", key)))
    monkeypatch.setattr(readiness.nfl, "load_pbp", lambda season: calls.append(("load", season)) or pbp())
    readiness.load_current_pbp(2026)
    assert calls == [("clear", "play_by_play_2026"), ("load", 2026)]


def test_nflverse_load_failure_is_clean_and_fail_closed(monkeypatch) -> None:
    monkeypatch.setattr(readiness.nfl, "clear_cache", lambda _key: None)
    monkeypatch.setattr(readiness.nfl, "load_pbp", lambda _season: (_ for _ in ()).throw(RuntimeError("offline")))
    with pytest.raises(readiness.Week2ReadinessError, match="refresh/load"):
        readiness.load_current_pbp(2026)


def test_schedule_identity_and_frozen_coefficient(tmp_path) -> None:
    row = readiness.audit_week2(schedule(tmp_path), pbp_loader=lambda _season: pbp())[0]
    assert (row["game"], row["home"], row["away"], row["kickoff"]) == (GAME["game_id"], "SEA", "NE", GAME["kickoff_at"])
    assert DEF_EPA_COEFFICIENT == pytest.approx(1.044827)
