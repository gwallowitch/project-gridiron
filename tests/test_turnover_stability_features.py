from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.turnover_stability import (
    build_turnover_stability_features,
)


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
            "game_id": ["g1"] * 8 + ["g2", "g2"],
            "season": [2024] * 10,
            "week": [1] * 8 + [2, 2],
            "posteam": [
                "AAA", "AAA", "AAA", "AAA",
                "BBB", "BBB", "BBB", "BBB",
                "AAA", "BBB",
            ],
            "defteam": [
                "BBB", "BBB", "BBB", "BBB",
                "AAA", "AAA", "AAA", "AAA",
                "BBB", "AAA",
            ],
            "play_type": ["pass", "run", "pass", "run"] * 2 + ["pass", "run"],
            "interception": [1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
            "fumble": [0, 1, 0, 0, 0, 1, 0, 0, 0, 1],
            "fumble_lost": [0, 1, 0, 0, 0, 0, 0, 0, 0, 1],
        }
    )


def test_week_one_has_no_prior_history() -> None:
    out = build_turnover_stability_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_turnover_stability_known"] is False
    assert row["away_turnover_stability_known"] is False
    assert row["turnover_protection_advantage"] is None


def test_week_two_uses_only_prior_week() -> None:
    out = build_turnover_stability_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_turnover_stability_known"] is True
    assert row["away_turnover_stability_known"] is True
    assert row["home_off_turnovers"] == 2
    assert row["away_off_turnovers"] == 0
    assert row["home_off_fumble_loss_rate"] == pytest.approx(1.0)
    assert row["away_off_fumble_loss_rate"] == pytest.approx(0.0)


def test_current_week_turnovers_do_not_leak() -> None:
    out = build_turnover_stability_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_off_interceptions_thrown"] == 1
    assert row["away_off_interceptions_thrown"] == 0


def test_takeaway_advantage_is_home_positive() -> None:
    out = build_turnover_stability_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    expected = (
        row["home_def_takeaway_rate"]
        - row["away_def_takeaway_rate"]
    )
    assert row["takeaway_creation_advantage"] == pytest.approx(expected)


def test_missing_required_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_turnover_stability_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
