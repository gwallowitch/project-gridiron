from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.passing import build_passing_features


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2024, 2024],
            "week": [1, 2],
            "home_team": ["AAA", "AAA"],
            "away_team": ["BBB", "BBB"],
        }
    )


def pbp() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g1", "g2", "g2"],
            "season": [2024] * 4,
            "week": [1, 1, 2, 2],
            "posteam": ["AAA", "BBB", "AAA", "BBB"],
            "defteam": ["BBB", "AAA", "BBB", "AAA"],
            "pass_attempt": [1, 1, 1, 1],
            "sack": [0, 1, 0, 0],
            "epa": [0.8, -1.2, 50.0, -50.0],
            "success": [1.0, 0.0, 1.0, 0.0],
            "yards_gained": [25.0, -7.0, 80.0, -5.0],
        }
    )


def test_week_one_has_no_prior_passing_history() -> None:
    out = build_passing_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_passing_known"] is False
    assert row["away_passing_known"] is False
    assert row["pass_off_epa_difference"] is None


def test_week_two_uses_only_week_one() -> None:
    out = build_passing_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_passing_known"] is True
    assert row["away_passing_known"] is True
    assert row["home_off_pass_epa_per_dropback"] == pytest.approx(0.8)
    assert row["away_off_pass_epa_per_dropback"] == pytest.approx(-1.2)
    assert row["home_off_explosive_pass_rate"] == pytest.approx(1.0)
    assert row["away_off_sack_rate"] == pytest.approx(1.0)


def test_current_week_extremes_cannot_leak() -> None:
    out = build_passing_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert abs(row["home_off_pass_epa_per_dropback"]) < 10
    assert abs(row["away_off_pass_epa_per_dropback"]) < 10


def test_missing_required_pbp_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_passing_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
