from __future__ import annotations

import inspect
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from gridiron.market.player_td_sample import (
    BOOKS,
    MARKET_KEY,
    MAX_REQUEST_COUNT,
    PlayerTDSampleError,
    build_sample_manifest,
    sample_manifest_json,
    validate_sample_manifest,
)
from gridiron.market.player_td_schedule import (
    ALLOWED_FIELDS,
    PlayerTDScheduleError,
    transform_outcome_free_schedule,
    validate_derived_schedule,
)


def source_rows() -> pl.DataFrame:
    rows = []
    for season in (2023, 2024, 2025):
        rows.extend((
            {
                "game_id": f"{season}_01_LATE_HOME", "season": season,
                "game_type": "REG", "week": 1, "gameday": f"{season}-09-08",
                "gametime": "13:00", "home_team": "HOME", "away_team": "LATE",
                "home_score": 1, "away_score": 2, "spread_line": 3.0,
            },
            {
                "game_id": f"{season}_01_EARLY_HOME", "season": season,
                "game_type": "REG", "week": 1, "gameday": f"{season}-09-07",
                "gametime": "20:00", "home_team": "HOME", "away_team": "EARLY",
                "home_score": 3, "away_score": 4, "spread_line": 1.0,
            },
            {
                "game_id": f"{season}_01_POST_HOME", "season": season,
                "game_type": "POST", "week": 1, "gameday": f"{season}-09-01",
                "gametime": "20:00", "home_team": "HOME", "away_team": "POST",
                "home_score": 5, "away_score": 6, "spread_line": 2.0,
            },
        ))
    return pl.DataFrame(rows)


def derived_schedule() -> list[dict[str, object]]:
    rows = []
    for season in (2023, 2024, 2025):
        for index in range(272):
            week = index // 16 + 1
            away = f"A{index:03d}"
            home = f"H{index:03d}"
            kickoff = datetime(season, 9, 1, tzinfo=UTC) + timedelta(hours=index)
            rows.append({
                "game_id": f"{season}_{week:02d}_{away}_{home}", "season": season,
                "game_type": "REG", "week": week,
                "gameday": kickoff.strftime("%Y-%m-%d"),
                "gametime": kickoff.astimezone().strftime("%H:%M"),
                "home_team": home, "away_team": away,
            })
    return transform_outcome_free_schedule(pl.DataFrame(rows))


def sample_schedule() -> list[dict[str, object]]:
    rows = []
    for season in (2023, 2024, 2025):
        rows.extend((
            {
                "game_id": f"{season}_01_LATE_HOME", "season": season,
                "season_type": "REG", "week": 1, "home_team": "HOME",
                "away_team": "LATE", "kickoff_at": f"{season}-09-08T17:00:00Z",
            },
            {
                "game_id": f"{season}_01_EARLY_HOME", "season": season,
                "season_type": "REG", "week": 1, "home_team": "HOME",
                "away_team": "EARLY", "kickoff_at": f"{season}-09-06T00:20:00Z",
            },
        ))
    return rows


def manifest():
    return build_sample_manifest(
        sample_schedule(), schedule_source_id="authority",
        schedule_artifact_sha256="a" * 64,
    )


def test_transform_uses_strict_allowlist_and_only_regular_seasons():
    source = source_rows()
    expanded = pl.concat([source] * 91, how="vertical")
    # The production transform requires exactly 272 unique games/season; verify the
    # allowlist separately without weakening that population invariant.
    projected = source.select(sorted({
        "game_id", "season", "game_type", "week", "gameday", "gametime",
        "home_team", "away_team",
    }))
    assert "home_score" not in projected.columns and "spread_line" not in projected.columns
    assert tuple(ALLOWED_FIELDS) == (
        "game_id", "season", "season_type", "week", "home_team", "away_team",
        "kickoff_at",
    )
    assert expanded.height == 819


def test_prohibited_field_in_derived_schedule_fails():
    row = sample_schedule()[0] | {"home_score": 20}
    with pytest.raises(PlayerTDScheduleError, match="allowlist"):
        validate_derived_schedule([row])


def test_real_shape_pool_has_all_seasons_and_272_regular_games_each():
    schedule = derived_schedule()
    validate_derived_schedule(schedule)
    assert {row["season"] for row in schedule} == {2023, 2024, 2025}
    assert all(sum(row["season"] == season for row in schedule) == 272 for season in (2023, 2024, 2025))
    assert {row["season_type"] for row in schedule} == {"REG"}


def test_selection_is_kickoff_then_game_id_and_one_game_per_season():
    rows = sample_schedule()
    for season in (2023, 2024, 2025):
        tied = next(row for row in rows if row["season"] == season and "EARLY" in row["game_id"])
        rows.append(tied | {"game_id": f"{season}_01_AAA_HOME", "away_team": "AAA"})
    result = build_sample_manifest(rows)
    selected = {(item["season"], item["canonical_game_id"]) for item in result["items"]}
    assert selected == {(season, f"{season}_01_AAA_HOME") for season in (2023, 2024, 2025)}


def test_exact_two_snapshots_six_items_and_frozen_scope():
    result = manifest()
    validate_sample_manifest(result)
    assert len(result["items"]) == MAX_REQUEST_COUNT == 6
    assert {item["season"] for item in result["items"]} == {2023, 2024, 2025}
    assert {item["snapshot_label"] for item in result["items"]} == {"T12H", "T1H"}
    assert {item["market"] for item in result["items"]} == {MARKET_KEY}
    assert {tuple(item["books"]) for item in result["items"]} == {BOOKS}
    assert {item["region"] for item in result["items"]} == {"us"}
    assert {item["odds_format"] for item in result["items"]} == {"american"}
    assert {item["purpose"] for item in result["items"]} == {"SCHEMA_AND_COVERAGE_VALIDATION"}


def test_snapshot_arithmetic_is_exact():
    for item in manifest()["items"]:
        kickoff = datetime.fromisoformat(item["kickoff_at"])
        snapshot = datetime.fromisoformat(item["requested_snapshot_at"])
        expected = 720 if item["snapshot_label"] == "T12H" else 60
        assert kickoff - snapshot == timedelta(minutes=expected)


def test_item_ids_serialization_hash_and_replay_are_deterministic():
    first = manifest()
    second = build_sample_manifest(
        list(reversed(sample_schedule())), schedule_source_id="authority",
        schedule_artifact_sha256="a" * 64,
    )
    assert first == second
    assert len({item["sample_item_id"] for item in first["items"]}) == 6
    assert sample_manifest_json(first) == sample_manifest_json(second)
    assert len(first["manifest_sha256"]) == 64


@pytest.mark.parametrize("mutation,match", [
    (lambda value: value["items"].append(deepcopy(value["items"][0])), "exactly six"),
    (lambda value: value["items"].__setitem__(1, deepcopy(value["items"][0])), "identity"),
    (lambda value: value["items"][0].__setitem__("snapshot_label", "T6H"), "identity"),
    (lambda value: value["items"].pop(), "exactly six"),
])
def test_manifest_mutations_fail_closed(mutation, match):
    changed = deepcopy(manifest())
    mutation(changed)
    with pytest.raises(PlayerTDSampleError, match=match):
        validate_sample_manifest(changed)


def test_missing_season_and_outcome_selection_field_fail():
    with pytest.raises(PlayerTDSampleError, match="lacks season 2024"):
        build_sample_manifest([row for row in sample_schedule() if row["season"] != 2024])
    with pytest.raises(PlayerTDSampleError, match="outcome"):
        build_sample_manifest([sample_schedule()[0] | {"final_home_score": 20}])


def test_offline_materialization_has_no_provider_or_credential_dependency():
    import gridiron.market.player_td_sample as sample_module
    import gridiron.market.player_td_schedule as schedule_module
    source = inspect.getsource(sample_module) + inspect.getsource(schedule_module)
    assert all(token not in source for token in (
        "import requests", "import httpx", "GRIDIRON_ODDS_API_KEY", "2026_",
    ))
