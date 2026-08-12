from __future__ import annotations

from datetime import UTC, datetime

import polars as pl

from gridiron.features.injuries import (
    build_game_injury_features,
    normalize_injury_reports,
)


def raw(status: str | None, practice: str | None, when: datetime) -> pl.DataFrame:
    return pl.DataFrame({
        "season":[2024],"game_type":["REG"],"team":["AAA"],"week":[1],
        "gsis_id":["p1"],"position":["WR"],"full_name":["Player One"],
        "first_name":["Player"],"last_name":["One"],
        "report_primary_injury":["Ankle"],"report_secondary_injury":[None],
        "report_status":[status],"practice_primary_injury":["Ankle"],
        "practice_secondary_injury":[None],"practice_status":[practice],
        "date_modified":[when],
    })


def test_report_severity_ordering() -> None:
    vals = {}
    for status in ("Questionable","Doubtful","Out"):
        vals[status] = normalize_injury_reports(
            raw(status, None, datetime(2024,9,6,tzinfo=UTC))
        )["report_severity"].item()
    assert vals["Out"] > vals["Doubtful"] > vals["Questionable"]


def test_practice_severity_ordering() -> None:
    statuses = [
        "Did Not Participate In Practice",
        "Limited Participation in Practice",
        "Full Participation in Practice",
    ]
    vals = [
        normalize_injury_reports(
            raw(None, s, datetime(2024,9,6,tzinfo=UTC))
        )["practice_severity"].item()
        for s in statuses
    ]
    assert vals[0] > vals[1] > vals[2]


def test_note_is_neutral() -> None:
    row = normalize_injury_reports(
        raw("Note","Note",datetime(2024,9,6,tzinfo=UTC))
    ).row(0,named=True)
    assert row["player_injury_severity"] == 0.0


def test_exact_kickoff_is_excluded() -> None:
    kickoff = datetime(2024,9,8,17,tzinfo=UTC)
    schedule = pl.DataFrame({
        "game_id":["g1"],"season":[2024],"week":[1],
        "home_team":["AAA"],"away_team":["BBB"],"kickoff_at":[kickoff],
    })
    injuries = normalize_injury_reports(raw("Out",None,kickoff))
    row = build_game_injury_features(schedule, injuries).row(0,named=True)
    assert row["home_injury_score"] == 0.0


def test_earlier_same_week_is_eligible() -> None:
    kickoff = datetime(2024,9,8,17,tzinfo=UTC)
    schedule = pl.DataFrame({
        "game_id":["g1"],"season":[2024],"week":[1],
        "home_team":["AAA"],"away_team":["BBB"],"kickoff_at":[kickoff],
    })
    injuries = normalize_injury_reports(
        raw("Out",None,datetime(2024,9,6,tzinfo=UTC))
    )
    row = build_game_injury_features(schedule, injuries).row(0,named=True)
    assert row["home_injury_score"] == 1.0
