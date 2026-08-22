from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.neutral_state import build_neutral_state_features


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
            "game_id": [
                "g1",
                "g1",
                "g1",
                "g1",
                "g1",
                "g2",
                "g2",
            ],
            "season": [2024] * 7,
            "week": [1, 1, 1, 1, 1, 2, 2],
            "posteam": ["AAA", "AAA", "BBB", "BBB", "AAA", "AAA", "BBB"],
            "defteam": ["BBB", "BBB", "AAA", "AAA", "BBB", "BBB", "AAA"],
            "play_type": ["run", "pass", "pass", "run", "pass", "run", "pass"],
            "epa": [0.4, -0.2, 0.5, -0.1, 99.0, -99.0, 99.0],
            "yards_gained": [6.0, 3.0, 20.0, 2.0, 99.0, 99.0, 99.0],
            "score_differential": [0.0, 7.0, -3.0, 8.0, 17.0, 0.0, 0.0],
            "game_seconds_remaining": [3000.0, 2200.0, 1800.0, 1000.0, 1600.0, 2500.0, 2500.0],
        }
    )


def test_week_one_has_no_prior_neutral_history() -> None:
    out = build_neutral_state_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_neutral_state_known"] is False
    assert row["away_neutral_state_known"] is False
    assert row["neutral_off_epa_difference"] is None


def test_week_two_uses_only_prior_neutral_plays() -> None:
    out = build_neutral_state_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_neutral_state_known"] is True
    assert row["away_neutral_state_known"] is True
    assert row["home_off_neutral_plays"] == 2
    assert row["away_off_neutral_plays"] == 2


def test_non_neutral_score_margin_is_excluded() -> None:
    out = build_neutral_state_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert abs(row["home_off_neutral_epa"]) < 10


def test_current_week_extremes_do_not_leak() -> None:
    out = build_neutral_state_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert abs(row["home_off_neutral_epa"]) < 10
    assert abs(row["away_off_neutral_epa"]) < 10


def test_explosive_rate_uses_15_yards() -> None:
    out = build_neutral_state_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 2).row(0, named=True)

    assert row["home_off_neutral_explosive_rate"] == pytest.approx(0.0)
    assert row["away_off_neutral_explosive_rate"] == pytest.approx(0.5)


def test_missing_required_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_neutral_state_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
