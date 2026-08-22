from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.drive_efficiency import build_drive_efficiency_features


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
            "fixed_drive": [1, 1, 2, 2, 1, 2],
            "fixed_drive_result": [
                "Touchdown",
                "Touchdown",
                "Punt",
                "Punt",
                "Touchdown",
                "Field goal",
            ],
            "epa": [0.5, 0.7, -0.4, -0.6, 99.0, -99.0],
        }
    )


def test_week_one_has_no_prior_drive_history() -> None:
    out = build_drive_efficiency_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_drive_efficiency_known"] is False
    assert row["away_drive_efficiency_known"] is False
    assert row["drive_off_epa_difference"] is None


def test_week_two_uses_only_prior_drives() -> None:
    out = build_drive_efficiency_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_drive_efficiency_known"] is True
    assert row["away_drive_efficiency_known"] is True
    assert row["home_off_epa_per_drive"] == pytest.approx(1.2)
    assert row["away_off_epa_per_drive"] == pytest.approx(-1.0)
    assert row["home_off_scoring_drive_rate"] == pytest.approx(1.0)
    assert row["away_off_scoring_drive_rate"] == pytest.approx(0.0)
    assert row["home_off_td_drive_rate"] == pytest.approx(1.0)


def test_current_week_extremes_cannot_leak() -> None:
    out = build_drive_efficiency_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert abs(row["home_off_epa_per_drive"]) < 10
    assert abs(row["away_off_epa_per_drive"]) < 10


def test_home_centered_differences_have_expected_orientation() -> None:
    out = build_drive_efficiency_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["drive_off_epa_difference"] > 0
    assert row["scoring_drive_rate_difference"] > 0
    assert row["td_drive_rate_difference"] > 0


def test_missing_required_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_drive_efficiency_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
