from __future__ import annotations

import polars as pl
import pytest

from gridiron.features.recent_form import build_recent_form_features


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1", "g2", "g3", "g4"],
            "season": [2024] * 4,
            "week": [1, 2, 3, 4],
            "home_team": ["AAA"] * 4,
            "away_team": ["BBB"] * 4,
        }
    )


def pbp() -> pl.DataFrame:
    rows = []
    for week, aaa_epa, bbb_epa in [
        (1, -0.3, 0.2),
        (2, 0.0, 0.1),
        (3, 0.4, -0.2),
        (4, 99.0, -99.0),
    ]:
        rows.extend(
            [
                {
                    "game_id": f"g{week}",
                    "season": 2024,
                    "week": week,
                    "posteam": "AAA",
                    "defteam": "BBB",
                    "play_type": "pass",
                    "epa": aaa_epa,
                },
                {
                    "game_id": f"g{week}",
                    "season": 2024,
                    "week": week,
                    "posteam": "BBB",
                    "defteam": "AAA",
                    "play_type": "pass",
                    "epa": bbb_epa,
                },
            ]
        )
    return pl.DataFrame(rows)


def test_week_one_has_no_recent_history() -> None:
    out = build_recent_form_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 1).row(0, named=True)

    assert row["home_recent_form_known"] is False
    assert row["recent_off_epa_difference"] is None


def test_week_three_has_two_prior_weeks_and_is_known() -> None:
    out = build_recent_form_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 3).row(0, named=True)

    assert row["home_recent_form_weeks"] == 2
    assert row["away_recent_form_weeks"] == 2
    assert row["home_recent_form_known"] is True
    assert row["away_recent_form_known"] is True


def test_week_four_recent_window_uses_prior_three_weeks_only() -> None:
    out = build_recent_form_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 4).row(0, named=True)

    assert row["home_recent_off_epa"] == pytest.approx(
        (-0.3 + 0.0 + 0.4) / 3
    )
    assert row["away_recent_off_epa"] == pytest.approx(
        (0.2 + 0.1 - 0.2) / 3
    )


def test_current_week_extremes_do_not_leak() -> None:
    out = build_recent_form_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 4).row(0, named=True)

    assert abs(row["home_recent_off_epa"]) < 1.0
    assert abs(row["away_recent_off_epa"]) < 1.0


def test_trend_is_recent_minus_season_to_date() -> None:
    out = build_recent_form_features(schedule(), pbp())
    row = out.filter(pl.col("week") == 4).row(0, named=True)

    expected = row["home_recent_off_epa"] - row["home_season_off_epa"]
    assert row["home_off_epa_trend"] == pytest.approx(expected)


def test_missing_required_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        build_recent_form_features(
            schedule(),
            pl.DataFrame({"season": [2024]}),
        )
