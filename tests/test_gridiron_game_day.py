from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
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

    def fake_runner(
        snapshot: dict[str, object],
        *,
        def_epa: float,
        def_epa_source: str = "caller-supplied",
    ) -> dict[str, object]:
        received.update(
            snapshot=snapshot,
            def_epa=def_epa,
            def_epa_source=def_epa_source,
        )
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


def test_cli_week1_uses_frozen_neutral_def_epa(
    schedule_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed = {
        "BetMGM": "2026-09-09T18:19:00Z",
        "FanDuel": "2026-09-09T18:19:00Z",
        "DraftKings": "2026-09-09T18:19:00Z",
    }

    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "test-key")
    monkeypatch.setattr(
        game_day,
        "fetch_live_prices",
        lambda _game: (PRICES, observed),
    )
    monkeypatch.setattr(
        game_day,
        "build_operational_prediction",
        lambda snapshot, *, def_epa, def_epa_source="caller-supplied": {
            "game_id": snapshot["game"]["game_id"],
            "def_epa": def_epa,
            "def_epa_source": def_epa_source,
        },
    )
    monkeypatch.setattr(
        game_day,
        "format_operational_prediction",
        lambda result: f"def_epa={result['def_epa']}",
    )

    result = game_day.main(
        ["--game", GAME["game_id"], "--schedule", str(schedule_path)]
    )

    output = capsys.readouterr()

    assert result == 0
    assert "DEF EPA: +0.000000" in output.out
    assert "def_epa=0.0" in output.out


def test_automatic_def_epa_week1_is_zero() -> None:
    game = dict(GAME)
    game["week"] = 1
    game["season_type"] = "REG"

    assert game_day.automatic_def_epa_for_game(game) == 0.0


def test_automatic_def_epa_uses_only_prior_weeks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = {
        "game_id": "2026_04_NE_SEA",
        "season": 2026,
        "week": 4,
        "season_type": "REG",
        "home_team": "SEA",
        "away_team": "NE",
        "kickoff_at": "2026-10-01T00:20:00Z",
    }

    pbp = pl.DataFrame(
        {
            "game_id": [
                "g1", "g1",
                "g2", "g2",
                "g3", "g3",
                "future", "future",
            ],
            "season": [2026] * 8,
            "week": [1, 1, 2, 2, 3, 3, 4, 4],
            "posteam": [
                "SEA", "NE",
                "SEA", "NE",
                "SEA", "NE",
                "SEA", "NE",
            ],
            "defteam": [
                "NE", "SEA",
                "NE", "SEA",
                "NE", "SEA",
                "NE", "SEA",
            ],
            "play_type": ["pass"] * 8,
            "epa": [
                0.30, -0.10,
                0.20, -0.20,
                0.10, -0.30,
                999.0, -999.0,
            ],
        }
    )

    monkeypatch.setattr(
        game_day.nfl,
        "load_pbp",
        lambda season: pbp,
    )

    value = game_day.automatic_def_epa_for_game(game)

    # Week 4 rows must be excluded entirely.
    assert value == pytest.approx(0.0)


def test_automatic_def_epa_fails_closed_when_history_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = {
        "game_id": "2026_02_NE_SEA",
        "season": 2026,
        "week": 2,
        "season_type": "REG",
        "home_team": "SEA",
        "away_team": "NE",
        "kickoff_at": "2026-09-17T00:20:00Z",
    }

    empty = pl.DataFrame(
        schema={
            "game_id": pl.String,
            "season": pl.Int64,
            "week": pl.Int64,
            "posteam": pl.String,
            "defteam": pl.String,
            "play_type": pl.String,
            "epa": pl.Float64,
        }
    )

    monkeypatch.setattr(
        game_day.nfl,
        "load_pbp",
        lambda season: empty,
    )

    with pytest.raises(
        game_day.GameDayInputError,
        match="no prior-week nflverse play-by-play",
    ):
        game_day.automatic_def_epa_for_game(game)


def test_live_snapshot_provider_is_truthful() -> None:
    observed = {
        "BetMGM": "2026-09-09T18:19:00Z",
        "FanDuel": "2026-09-09T18:19:00Z",
        "DraftKings": "2026-09-09T18:19:00Z",
    }

    snapshot = game_day.build_game_day_snapshot(
        GAME,
        PRICES,
        captured_at=CAPTURED,
        observed_at=observed,
        provider="the-odds-api-operational",
    )

    assert snapshot["provider"] == "the-odds-api-operational"


def test_manual_snapshot_provider_remains_manual() -> None:
    snapshot = game_day.build_game_day_snapshot(
        GAME,
        PRICES,
        captured_at=CAPTURED,
    )

    assert snapshot["provider"] == "manual-game-day-entry"


def test_live_odds_missing_required_book_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "test-key")

    payload = [
        {
            "home_team": "Seattle Seahawks",
            "away_team": "New England Patriots",
            "bookmakers": [
                {
                    "key": "betmgm",
                    "last_update": "2026-09-09T18:19:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {
                                    "name": "Seattle Seahawks",
                                    "price": -175,
                                },
                                {
                                    "name": "New England Patriots",
                                    "price": 145,
                                },
                            ],
                        }
                    ],
                },
                {
                    "key": "draftkings",
                    "last_update": "2026-09-09T18:19:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {
                                    "name": "Seattle Seahawks",
                                    "price": -170,
                                },
                                {
                                    "name": "New England Patriots",
                                    "price": 142,
                                },
                            ],
                        }
                    ],
                },
            ],
        }
    ]

    monkeypatch.setattr(
        game_day,
        "_fetch_json",
        lambda _url: payload,
    )

    with pytest.raises(
        game_day.GameDayInputError,
        match="FanDuel",
    ):
        game_day.fetch_live_prices(GAME)


def test_stale_live_bookmaker_timestamp_fails_closed() -> None:
    observed = {
        "BetMGM": "2026-09-09T17:50:00Z",
        "FanDuel": "2026-09-09T18:19:00Z",
        "DraftKings": "2026-09-09T18:19:00Z",
    }

    snapshot = game_day.build_game_day_snapshot(
        GAME,
        PRICES,
        captured_at=CAPTURED,
        observed_at=observed,
        provider="the-odds-api-operational",
    )

    with pytest.raises(
        game_day.OperationalPredictionError,
        match="fresh complete market data required",
    ):
        game_day.build_operational_prediction(
            snapshot,
            def_epa=0.0,
        )


def test_cli_live_path_records_api_provider(
    schedule_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = {
        "BetMGM": "2026-09-09T18:19:00Z",
        "FanDuel": "2026-09-09T18:19:00Z",
        "DraftKings": "2026-09-09T18:19:00Z",
    }
    received: dict[str, object] = {}

    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "test-key")
    monkeypatch.setattr(
        game_day,
        "fetch_live_prices",
        lambda _game: (PRICES, observed),
    )

    def fake_runner(
        snapshot: dict[str, object],
        *,
        def_epa: float,
        def_epa_source: str = "caller-supplied",
    ) -> dict[str, object]:
        received["provider"] = snapshot["provider"]
        received["def_epa_source"] = def_epa_source
        return {
            "def_epa": def_epa,
            "def_epa_source": def_epa_source,
        }

    monkeypatch.setattr(
        game_day,
        "build_operational_prediction",
        fake_runner,
    )
    monkeypatch.setattr(
        game_day,
        "format_operational_prediction",
        lambda _result: "ok",
    )

    result = game_day.main(
        [
            "--game",
            GAME["game_id"],
            "--schedule",
            str(schedule_path),
        ]
    )

    assert result == 0
    assert received["provider"] == "the-odds-api-operational"


def test_automatic_def_epa_refreshes_current_season_pbp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = {
        "game_id": "2026_04_NE_SEA",
        "season": 2026,
        "week": 4,
        "season_type": "REG",
        "home_team": "SEA",
        "away_team": "NE",
        "kickoff_at": "2026-10-01T00:20:00Z",
    }

    calls: list[tuple[str, object]] = []

    pbp = pl.DataFrame(
        {
            "game_id": ["g1", "g1", "g2", "g2", "g3", "g3"],
            "season": [2026] * 6,
            "week": [1, 1, 2, 2, 3, 3],
            "posteam": ["SEA", "NE", "SEA", "NE", "SEA", "NE"],
            "defteam": ["NE", "SEA", "NE", "SEA", "NE", "SEA"],
            "play_type": ["pass"] * 6,
            "epa": [0.30, -0.10, 0.20, -0.20, 0.10, -0.30],
        }
    )

    monkeypatch.setattr(
        game_day.nfl,
        "clear_cache",
        lambda pattern: calls.append(("clear", pattern)),
    )

    def fake_load_pbp(season: int) -> pl.DataFrame:
        calls.append(("load", season))
        return pbp

    monkeypatch.setattr(
        game_day.nfl,
        "load_pbp",
        fake_load_pbp,
    )

    game_day.automatic_def_epa_for_game(game)

    assert calls == [
        ("clear", "play_by_play_2026"),
        ("load", 2026),
    ]


def test_cli_week1_passes_neutral_def_epa_source(
    schedule_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = {
        "BetMGM": "2026-09-09T18:19:00Z",
        "FanDuel": "2026-09-09T18:19:00Z",
        "DraftKings": "2026-09-09T18:19:00Z",
    }
    received: dict[str, object] = {}

    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "test-key")
    monkeypatch.setattr(
        game_day,
        "fetch_live_prices",
        lambda _game: (PRICES, observed),
    )

    def fake_runner(
        snapshot: dict[str, object],
        *,
        def_epa: float,
        def_epa_source: str = "caller-supplied",
    ) -> dict[str, object]:
        received["def_epa"] = def_epa
        received["def_epa_source"] = def_epa_source
        return {
            "def_epa": def_epa,
            "def_epa_source": def_epa_source,
        }

    monkeypatch.setattr(
        game_day,
        "build_operational_prediction",
        fake_runner,
    )
    monkeypatch.setattr(
        game_day,
        "format_operational_prediction",
        lambda _result: "ok",
    )

    result = game_day.main(
        [
            "--game",
            GAME["game_id"],
            "--schedule",
            str(schedule_path),
        ]
    )

    assert result == 0
    assert received["def_epa"] == 0.0
    assert received["def_epa_source"] == "frozen Week 1 neutral rule"


def test_cli_history_persistence_does_not_fetch_twice(
    schedule_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = {
        "BetMGM": "2026-09-09T18:19:00Z",
        "FanDuel": "2026-09-09T18:19:00Z",
        "DraftKings": "2026-09-09T18:19:00Z",
    }
    fetches = 0

    def fetch_once(_game: dict[str, object]):
        nonlocal fetches
        fetches += 1
        return PRICES, observed

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return CAPTURED

    history = tmp_path / "operational.jsonl"
    monkeypatch.setattr(game_day, "fetch_live_prices", fetch_once)
    monkeypatch.setattr(game_day, "datetime", FixedDateTime)
    result = game_day.main(
        [
            "--game",
            GAME["game_id"],
            "--schedule",
            str(schedule_path),
            "--record-history",
            "--history-path",
            str(history),
        ]
    )
    assert result == 0
    assert fetches == 1
    assert len(history.read_text(encoding="utf-8").splitlines()) == 1


def test_cli_week2_passes_automatic_nflverse_def_epa_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = dict(GAME)
    game["game_id"] = "2026_02_NE_SEA"
    game["week"] = 2
    game["kickoff_at"] = "2026-09-17T00:20:00Z"

    schedule = tmp_path / "schedule.json"
    schedule.write_text(json.dumps([game]), encoding="utf-8")

    observed = {
        "BetMGM": "2026-09-16T18:19:00Z",
        "FanDuel": "2026-09-16T18:19:00Z",
        "DraftKings": "2026-09-16T18:19:00Z",
    }
    received: dict[str, object] = {}

    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "test-key")
    monkeypatch.setattr(
        game_day,
        "fetch_live_prices",
        lambda _game: (PRICES, observed),
    )
    monkeypatch.setattr(
        game_day,
        "automatic_def_epa_for_game",
        lambda _game: 0.123456,
    )

    def fake_runner(
        snapshot: dict[str, object],
        *,
        def_epa: float,
        def_epa_source: str = "caller-supplied",
    ) -> dict[str, object]:
        received["def_epa"] = def_epa
        received["def_epa_source"] = def_epa_source
        return {
            "def_epa": def_epa,
            "def_epa_source": def_epa_source,
        }

    monkeypatch.setattr(
        game_day,
        "build_operational_prediction",
        fake_runner,
    )
    monkeypatch.setattr(
        game_day,
        "format_operational_prediction",
        lambda _result: "ok",
    )

    result = game_day.main(
        [
            "--game",
            game["game_id"],
            "--schedule",
            str(schedule),
        ]
    )

    assert result == 0
    assert received["def_epa"] == pytest.approx(0.123456)
    assert (
        received["def_epa_source"]
        == "automatic nflverse frozen feature"
    )


def test_automatic_def_epa_fails_closed_when_immediately_prior_week_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = {
        "game_id": "2026_04_NE_SEA",
        "season": 2026,
        "week": 4,
        "season_type": "REG",
        "home_team": "SEA",
        "away_team": "NE",
        "kickoff_at": "2026-10-01T00:20:00Z",
    }

    pbp = pl.DataFrame(
        {
            "game_id": ["g1", "g1", "g2", "g2"],
            "season": [2026] * 4,
            "week": [1, 1, 2, 2],
            "posteam": ["SEA", "NE", "SEA", "NE"],
            "defteam": ["NE", "SEA", "NE", "SEA"],
            "play_type": ["pass"] * 4,
            "epa": [0.30, -0.10, 0.20, -0.20],
        }
    )

    monkeypatch.setattr(game_day.nfl, "clear_cache", lambda _pattern: None)
    monkeypatch.setattr(game_day.nfl, "load_pbp", lambda _season: pbp)

    with pytest.raises(
        game_day.GameDayInputError,
        match="missing immediately prior week 3",
    ):
        game_day.automatic_def_epa_for_game(game)


def test_automatic_def_epa_accepts_immediately_prior_week(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = {
        "game_id": "2026_04_NE_SEA",
        "season": 2026,
        "week": 4,
        "season_type": "REG",
        "home_team": "SEA",
        "away_team": "NE",
        "kickoff_at": "2026-10-01T00:20:00Z",
    }

    pbp = pl.DataFrame(
        {
            "game_id": ["g1", "g1", "g3", "g3"],
            "season": [2026] * 4,
            "week": [1, 1, 3, 3],
            "posteam": ["SEA", "NE", "SEA", "NE"],
            "defteam": ["NE", "SEA", "NE", "SEA"],
            "play_type": ["pass"] * 4,
            "epa": [0.30, -0.10, 0.10, -0.30],
        }
    )

    monkeypatch.setattr(game_day.nfl, "clear_cache", lambda _pattern: None)
    monkeypatch.setattr(game_day.nfl, "load_pbp", lambda _season: pbp)

    value = game_day.automatic_def_epa_for_game(game)

    assert isinstance(value, float)
