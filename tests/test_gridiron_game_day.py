from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts import gridiron_game_day as game_day

GAME = {
    "game_id": "2026_01_NE_SEA",
    "season": 2026,
    "season_type": "REG",
    "week": 1,
    "away_team": "NE",
    "home_team": "SEA",
    "kickoff_at": "2026-09-10T00:20:00Z",
    "provider_ids": ["2026_01_NE_SEA"],
}
PRICES = {
    "BetMGM": (120, -140),
    "FanDuel": (122, -142),
    "DraftKings": (121, -141),
}
CAPTURED = datetime(2026, 9, 9, 18, 20, tzinfo=UTC)


@pytest.fixture
def schedule_path(tmp_path: Path) -> Path:
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps([GAME]), encoding="utf-8")
    return path


def test_retained_schedule_is_available_and_unambiguous() -> None:
    schedule = game_day.load_schedule()
    assert len(schedule) == 240
    game = game_day.resolve_game("2026_01_NE_SEA", schedule)
    assert game["away_team"] == "NE"
    assert game["home_team"] == "SEA"
    assert game["kickoff_at"] == "2026-09-10T00:20:00Z"


def test_schedule_lookup_is_exact_and_populates_identity(schedule_path: Path) -> None:
    schedule = game_day.load_schedule(schedule_path)
    assert game_day.resolve_game("2026_01_NE_SEA", schedule) == GAME
    with pytest.raises(game_day.GameDayInputError, match="not found"):
        game_day.resolve_game("2026_01_SEA_NE", schedule)


def test_duplicate_game_identity_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps([GAME, GAME]), encoding="utf-8")
    with pytest.raises(game_day.GameDayInputError, match="duplicate"):
        game_day.load_schedule(path)


def test_snapshot_maps_six_prices_and_fixed_clock() -> None:
    snapshot = game_day.build_game_day_snapshot(GAME, PRICES, captured_at=CAPTURED)
    assert snapshot["captured_at"] == "2026-09-09T18:20:00Z"
    assert snapshot["game"]["kickoff_at"] == GAME["kickoff_at"]
    assert [offer["book"] for offer in snapshot["offers"]] == [
        "BetMGM",
        "FanDuel",
        "DraftKings",
    ]
    mapped = [
        (offer["home_odds"], offer["away_odds"])
        for offer in snapshot["offers"]
    ]
    assert mapped == [(120, -140), (122, -142), (121, -141)]


def test_missing_book_is_rejected() -> None:
    incomplete = dict(PRICES)
    incomplete.pop("FanDuel")
    with pytest.raises(game_day.GameDayInputError, match="FanDuel"):
        game_day.build_game_day_snapshot(GAME, incomplete, captured_at=CAPTURED)


@pytest.mark.parametrize("odds", [0, 99, -99])
def test_invalid_odds_are_rejected_by_existing_runner(
    schedule_path: Path, odds: int
) -> None:
    prices = dict(PRICES)
    prices["BetMGM"] = (odds, -140)
    with pytest.raises(ValueError, match="home_odds"):
        game_day.run_game_day(
            GAME["game_id"],
            prices,
            def_epa=0.1,
            captured_at=CAPTURED,
            schedule_path=schedule_path,
        )


def test_def_epa_is_explicit_and_post_kickoff_rejects(schedule_path: Path) -> None:
    with pytest.raises(TypeError, match="def_epa"):
        game_day.run_game_day(  # type: ignore[call-arg]
            GAME["game_id"],
            PRICES,
            captured_at=CAPTURED,
            schedule_path=schedule_path,
        )
    with pytest.raises(ValueError, match="pre-kickoff"):
        game_day.run_game_day(
            GAME["game_id"],
            PRICES,
            def_epa=0.1,
            captured_at=datetime(2026, 9, 10, 0, 20, tzinfo=UTC),
            schedule_path=schedule_path,
        )


def test_existing_operational_runner_is_reused(
    monkeypatch: pytest.MonkeyPatch, schedule_path: Path
) -> None:
    received: dict[str, object] = {}

    def fake_runner(snapshot: dict[str, object], *, def_epa: float) -> dict[str, object]:
        received.update(snapshot=snapshot, def_epa=def_epa)
        return {"sentinel": True}

    monkeypatch.setattr(game_day, "build_operational_prediction", fake_runner)
    result = game_day.run_game_day(
        GAME["game_id"],
        PRICES,
        def_epa=0.125,
        captured_at=CAPTURED,
        schedule_path=schedule_path,
    )
    assert result == {"sentinel": True}
    assert received["def_epa"] == 0.125


def test_deterministic_prediction_and_no_prospective_writes(
    schedule_path: Path, tmp_path: Path
) -> None:
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    first = game_day.run_game_day(
        GAME["game_id"],
        PRICES,
        def_epa=0.125,
        captured_at=CAPTURED,
        schedule_path=schedule_path,
    )
    second = game_day.run_game_day(
        GAME["game_id"],
        PRICES,
        def_epa=0.125,
        captured_at=CAPTURED,
        schedule_path=schedule_path,
    )
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert first == second
    assert before == after
    assert first["game_id"] == GAME["game_id"]
    assert first["def_epa"] == 0.125


def test_cli_requires_human_def_epa_when_not_supplied(
    schedule_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    values = iter(["120", "-140", "122", "-142", "121", "-141"])

    def entered_value(_prompt: str) -> str:
        try:
            return next(values)
        except StopIteration as exc:
            raise EOFError from exc

    monkeypatch.setattr("builtins.input", entered_value)
    result = game_day.main(
        ["--game", GAME["game_id"], "--schedule", str(schedule_path)]
    )
    assert result == 2
    assert "invalid def_epa_trend_advantage" in capsys.readouterr().err
