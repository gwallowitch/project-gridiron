from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.pressure import build_pressure_features


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
            "game_id": ["g1", "g1", "g1", "g1", "g2", "g2"],
            "season": [2024] * 6,
            "week": [1, 1, 1, 1, 2, 2],
            "posteam": ["AAA", "AAA", "BBB", "BBB", "AAA", "BBB"],
            "defteam": ["BBB", "BBB", "AAA", "AAA", "BBB", "AAA"],
            "play_type": ["pass"] * 6,
            "qb_hit": [1, 0, 0, 1, 1, 0],
            "sack": [0, 0, 0, 1, 1, 0],
            "epa": [-0.5, 0.8, 0.6, -1.0, -99.0, 99.0],
        }
    )


def test_week_one_has_no_prior_pressure_history() -> None:
    out = build_pressure_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_pressure_known"] is False
    assert row["away_pressure_known"] is False
    assert row["pass_protection_advantage"] is None


def test_week_two_uses_only_prior_pressure_history() -> None:
    out = build_pressure_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_pressure_known"] is True
    assert row["away_pressure_known"] is True
    assert row["home_off_pressure_allowed_rate"] == pytest.approx(0.5)
    assert row["away_off_pressure_allowed_rate"] == pytest.approx(0.5)
    assert row["home_off_clean_dropback_rate"] == pytest.approx(0.5)
    assert row["away_off_clean_dropback_rate"] == pytest.approx(0.5)


def test_current_week_extremes_do_not_leak() -> None:
    out = build_pressure_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert abs(row["home_off_pressured_epa"]) < 10
    assert abs(row["away_off_pressured_epa"]) < 10


def test_pressure_proxy_counts_qb_hit_or_sack_once() -> None:
    out = build_pressure_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_off_pressure_events"] == 1
    assert row["away_off_pressure_events"] == 1


def test_home_centered_advantages_are_oriented_correctly() -> None:
    out = build_pressure_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["pass_protection_advantage"] == pytest.approx(0.0)
    assert row["pressure_creation_advantage"] == pytest.approx(0.0)


def test_non_pass_plays_are_excluded() -> None:
    extra = pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [1],
            "posteam": ["AAA"],
            "defteam": ["BBB"],
            "play_type": ["run"],
            "qb_hit": [1],
            "sack": [1],
            "epa": [-99.0],
        }
    )
    out = build_pressure_features(schedule(), pl.concat([pbp(), extra]))
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_off_dropbacks"] == 2


def test_missing_required_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_pressure_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
