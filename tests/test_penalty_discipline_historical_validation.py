from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl

SCRIPT = Path("scripts") / "validate_penalty_discipline_history.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_penalty_discipline_history",
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
                "home_penalty_discipline_known": week >= 3,
                "away_penalty_discipline_known": week >= 3,
                "home_discipline_history_weeks": max(week - 1, 0),
                "away_discipline_history_weeks": max(week - 1, 0),
                "home_discipline_off_plays": max((week - 1) * 60, 0),
                "away_discipline_off_plays": max((week - 1) * 60, 0),
                "home_discipline_def_plays": max((week - 1) * 60, 0),
                "away_discipline_def_plays": max((week - 1) * 60, 0),
                **{
                    name: (
                        None
                        if week < 2
                        else (week - 9) * 0.1
                    )
                    for name in FEATURES
                },
            }
        )

    return pl.DataFrame(rows)


def test_validate_season_measures_health(
    tmp_path: Path,
) -> None:
    path = tmp_path / "discipline.parquet"
    artifact().write_parquet(path)

    result = validate_season(path, 2024)

    assert result["rows"] == 18
    assert result["duplicate_game_ids"] == 0
    assert result["week3_plus_both_known_rate"] == 1.0
    assert result["features"][FEATURES[0]]["std"] > 0.0


def test_evaluate_accepts_healthy_report() -> None:
    stats = {
        "coverage": 0.95,
        "std": 0.10,
        "nonzero_rate": 0.90,
    }

    report = {
        "seasons": {
            "2024": {
                "rows": 285,
                "week3_plus_both_known_rate": 0.98,
                "features": {
                    name: dict(stats)
                    for name in FEATURES
                },
                "depth": {
                    "home_discipline_history_weeks": {
                        "mean": 8.0
                    },
                    "home_discipline_off_plays": {
                        "mean": 500.0
                    },
                    "home_discipline_def_plays": {
                        "mean": 500.0
                    },
                },
            }
        }
    }

    assert evaluate(report) == []


def test_evaluate_rejects_low_mature_coverage() -> None:
    stats = {
        "coverage": 0.95,
        "std": 0.10,
        "nonzero_rate": 0.90,
    }

    report = {
        "seasons": {
            "2024": {
                "rows": 285,
                "week3_plus_both_known_rate": 0.75,
                "features": {
                    name: dict(stats)
                    for name in FEATURES
                },
                "depth": {
                    "home_discipline_history_weeks": {
                        "mean": 8.0
                    },
                    "home_discipline_off_plays": {
                        "mean": 500.0
                    },
                    "home_discipline_def_plays": {
                        "mean": 500.0
                    },
                },
            }
        }
    }

    failures = evaluate(report)

    assert any(
        "week-3+" in failure
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
