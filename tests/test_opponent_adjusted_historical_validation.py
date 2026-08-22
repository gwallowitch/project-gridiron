from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl

SCRIPT = Path("scripts") / "validate_opponent_adjusted_history.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_opponent_adjusted_history",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None

MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

FEATURES = MODULE.FEATURES
evaluate = MODULE.evaluate
render_markdown = MODULE.render_markdown
validate_season = MODULE.validate_season


def artifact() -> pl.DataFrame:
    rows = []

    for week in range(1, 19):
        rows.append(
            {
                "game_id": f"g{week}",
                "season": 2024,
                "week": week,
                "home_opponent_adjusted_known": week >= 4,
                "away_opponent_adjusted_known": week >= 4,
                "home_opponent_adjusted_history_weeks": max(
                    week - 1,
                    0,
                ),
                "away_opponent_adjusted_history_weeks": max(
                    week - 1,
                    0,
                ),
                "home_opponent_adjusted_opponents": max(
                    week - 1,
                    0,
                ),
                "away_opponent_adjusted_opponents": max(
                    week - 1,
                    0,
                ),
                **{
                    name: (
                        None
                        if week < 3
                        else (week - 9) * 0.01
                    )
                    for name in FEATURES
                },
            }
        )

    return pl.DataFrame(rows)


def test_validate_season_measures_health(
    tmp_path: Path,
) -> None:
    path = tmp_path / "opp.parquet"
    artifact().write_parquet(path)

    result = validate_season(path, 2024)

    assert result["rows"] == 18
    assert result["duplicate_game_ids"] == 0
    assert result["week4_plus_both_known_rate"] == 1.0
    assert result["features"][FEATURES[0]]["std"] > 0.0


def test_evaluate_accepts_healthy_report() -> None:
    stats = {
        "coverage": 0.90,
        "std": 0.10,
        "nonzero_rate": 0.90,
    }

    report = {
        "seasons": {
            "2024": {
                "rows": 285,
                "week4_plus_both_known_rate": 0.95,
                "features": {
                    name: dict(stats)
                    for name in FEATURES
                },
                "depth": {
                    "home_opponent_adjusted_history_weeks": {
                        "mean": 8.0
                    },
                    "home_opponent_adjusted_opponents": {
                        "mean": 7.0
                    },
                },
            }
        }
    }

    assert evaluate(report) == []


def test_evaluate_rejects_low_mature_coverage() -> None:
    stats = {
        "coverage": 0.90,
        "std": 0.10,
        "nonzero_rate": 0.90,
    }

    report = {
        "seasons": {
            "2024": {
                "rows": 285,
                "week4_plus_both_known_rate": 0.70,
                "features": {
                    name: dict(stats)
                    for name in FEATURES
                },
                "depth": {
                    "home_opponent_adjusted_history_weeks": {
                        "mean": 8.0
                    },
                    "home_opponent_adjusted_opponents": {
                        "mean": 7.0
                    },
                },
            }
        }
    }

    failures = evaluate(report)

    assert any(
        "week-4+" in failure
        for failure in failures
    )


def test_markdown_states_no_predictive_claim() -> None:
    report = {
        "seasons": {},
        "failures": [],
    }

    text = render_markdown(report)

    assert "does not claim predictive lift" in text
    assert "does not promote" in text
