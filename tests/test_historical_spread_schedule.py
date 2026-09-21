from __future__ import annotations

import hashlib
import inspect
import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest

from gridiron.market.historical_spread_manifest import (
    estimate_cost,
    validate_historical_manifest,
)
from gridiron.market.historical_spread_schedule import (
    ALLOWED_FIELDS,
    SOURCE_SHA256,
    HistoricalScheduleError,
    build_review_report,
    transform_outcome_free_schedule,
    validate_schedule_provenance,
)

ROOT = Path(__file__).parents[1]
ARTIFACTS = ROOT / "data/reference/historical_spread_acquisition_v1"
EXPECTED_GAMES = (
    "2021_02_NYG_WAS", "2021_02_BUF_MIA", "2021_08_GB_ARI",
    "2021_08_CAR_ATL", "2021_15_KC_LAC", "2021_15_NE_IND",
    "2021_19_LV_CIN", "2023_02_MIN_PHI", "2023_02_BAL_CIN",
    "2023_08_TB_BUF", "2023_08_ATL_TEN", "2023_15_LAC_LV",
    "2023_15_MIN_CIN", "2023_19_CLE_HOU", "2025_02_WAS_GB",
    "2025_02_BUF_NYJ", "2025_08_MIN_LAC", "2025_08_BUF_CAR",
    "2025_15_ATL_TB", "2025_15_ARI_HOU", "2025_19_LA_CAR",
)
FORBIDDEN = {
    "away_score", "home_score", "final_home_score", "final_away_score",
    "winner", "result", "margin", "ats_margin", "cover_side", "total",
    "profit", "roi", "spread_line", "home_spread_odds", "away_spread_odds",
}


def source_frame() -> pl.DataFrame:
    rows = []
    for season in (2021, 2023, 2025):
        for game_type, weeks in (("REG", (2, 8, 15)), ("WC", (19,))):
            for week in weeks:
                for index in range(3 if game_type == "REG" else 2):
                    away, home = f"A{index}", f"H{index}"
                    rows.append(
                        {
                            "game_id": f"{season}_{week:02d}_{away}_{home}",
                            "season": season, "game_type": game_type, "week": week,
                            "gameday": f"{season}-09-{week:02d}", "gametime": f"{13 + index}:00",
                            "away_team": away, "home_team": home,
                            "away_score": 99, "home_score": 0, "result": -99,
                            "spread_line": 7.5, "home_spread_odds": -110,
                        }
                    )
    return pl.DataFrame(rows)


def load_artifacts():
    schedule_bytes = (ARTIFACTS / "historical_spread_schedule_v1.json").read_bytes()
    manifest_bytes = (ARTIFACTS / "step92f_manifest.json").read_bytes()
    return json.loads(schedule_bytes), json.loads(manifest_bytes), schedule_bytes, manifest_bytes


def test_transform_is_deterministic_and_explicitly_outcome_free():
    frame = source_frame()
    first = transform_outcome_free_schedule(frame)
    second = transform_outcome_free_schedule(frame.reverse())
    assert first == second
    assert all(tuple(row) == ALLOWED_FIELDS for row in first)
    assert not any(FORBIDDEN & {key.lower() for key in row} for row in first)


def test_transform_normalizes_utc_types_weeks_and_game_ids():
    rows = transform_outcome_free_schedule(source_frame())
    assert {row["season_type"] for row in rows} == {"REG", "WC"}
    assert {row["week"] for row in rows if row["season_type"] == "REG"} == {2, 8, 15}
    assert {row["week"] for row in rows if row["season_type"] == "WC"} == {19}
    assert all(row["kickoff_at"].endswith("Z") for row in rows)
    assert all(row["game_id"] == f"{row['season']}_{row['week']:02d}_{row['away_team']}_{row['home_team']}" for row in rows)


def test_transform_rejects_bad_identity_and_incomplete_coverage():
    bad = source_frame().with_columns(
        pl.when(pl.arange(0, pl.len()) == 0).then(pl.lit("wrong")).otherwise(pl.col("game_id")).alias("game_id")
    )
    with pytest.raises(HistoricalScheduleError, match="canonical game identity"):
        transform_outcome_free_schedule(bad)
    incomplete = source_frame().filter(~((pl.col("season") == 2025) & (pl.col("game_type") == "WC")))
    with pytest.raises(HistoricalScheduleError, match="frozen sample"):
        transform_outcome_free_schedule(incomplete)


def test_retained_schedule_and_sha_are_stable_and_outcome_free():
    schedule, _manifest, schedule_bytes, _manifest_bytes = load_artifacts()
    assert hashlib.sha256(schedule_bytes).hexdigest() == "db263a3df39bd1d72a3882168328b833fbc1327f61d3a2e1eac991f3bfdf1128"
    assert (ARTIFACTS / "historical_spread_schedule_v1.sha256").read_text().strip() == hashlib.sha256(schedule_bytes).hexdigest()
    assert len(schedule) == 158
    assert all(set(row) == set(ALLOWED_FIELDS) for row in schedule)
    assert not any(FORBIDDEN & {key.lower() for key in row} for row in schedule)


def test_provenance_is_pinned_and_valid():
    provenance = json.loads(
        (ARTIFACTS / "schedule_provenance.json").read_text(encoding="utf-8")
    )
    validate_schedule_provenance(provenance)
    assert provenance["source_sha256"] == SOURCE_SHA256
    assert provenance["raw_retained"] is False


def test_final_manifest_is_valid_stable_and_has_exact_distributions():
    _schedule, manifest, _schedule_bytes, manifest_bytes = load_artifacts()
    validate_historical_manifest(manifest)
    assert manifest["manifest_sha256"] == "e45976ed4768335095d3f6298a039c40a9ec1edb82361dddc11064e9ed8d464d"
    assert (ARTIFACTS / "step92f_manifest.sha256").read_text().strip() == manifest["manifest_sha256"]
    assert manifest_bytes.endswith(b"\n")
    assert len(manifest["items"]) == 105
    assert {season: sum(item["season"] == season for item in manifest["items"]) for season in (2021, 2023, 2025)} == {2021: 35, 2023: 35, 2025: 35}
    assert {target: sum(item["target_label"] == target for item in manifest["items"]) for target in manifest["targets"]} == {target: 21 for target in manifest["targets"]}
    assert all(sum(item["canonical_game_id"] == game for item in manifest["items"]) == 5 for game in EXPECTED_GAMES)


def test_selected_games_match_frozen_order_without_outcomes():
    _schedule, manifest, _schedule_bytes, _manifest_bytes = load_artifacts()
    ordered = []
    for item in manifest["items"]:
        if item["canonical_game_id"] not in ordered:
            ordered.append(item["canonical_game_id"])
    expected = sorted(
        EXPECTED_GAMES,
        key=lambda game: next((item["target_timestamp"], item["manifest_item_id"]) for item in manifest["items"] if item["canonical_game_id"] == game),
    )
    assert ordered == expected


def test_review_is_outcome_free_and_lists_all_games():
    schedule, manifest, _schedule_bytes, _manifest_bytes = load_artifacts()
    report = build_review_report(schedule, manifest)
    assert report == (ARTIFACTS / "step92f_manifest_review.md").read_text(
        encoding="utf-8"
    )
    lowered = report.lower()
    assert all(field not in lowered for field in FORBIDDEN)
    assert all(game in report for game in EXPECTED_GAMES)


def test_exact_credit_estimate_uses_frozen_estimator():
    assert estimate_cost(105, credits_per_request=10)["estimated_total_credits"] == 1050


def test_schedule_and_manifest_generation_have_no_network_or_secret_access():
    import gridiron.market.historical_spread_schedule as module
    source = inspect.getsource(module)
    assert all(token not in source for token in ("requests", "httpx", "urllib", "socket", "GRIDIRON_ODDS_API_KEY"))


def test_provenance_timestamp_is_timezone_aware():
    provenance = json.loads(
        (ARTIFACTS / "schedule_provenance.json").read_text(encoding="utf-8")
    )
    assert datetime.fromisoformat(provenance["retrieved_at"]).tzinfo == UTC
