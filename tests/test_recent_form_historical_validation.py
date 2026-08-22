from __future__ import annotations

import importlib.util
from pathlib import Path

import polars as pl

_SCRIPT = Path("scripts") / "validate_recent_form_history.py"
_SPEC = importlib.util.spec_from_file_location("validate_recent_form_history", _SCRIPT)
assert _SPEC is not None
assert _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

FEATURES = _MODULE.FEATURES
evaluate = _MODULE.evaluate
render_markdown = _MODULE.render_markdown
validate_season = _MODULE.validate_season


def artifact() -> pl.DataFrame:
    rows = []
    for week in range(1, 19):
        rows.append(
            {
                "game_id": f"g{week}",
                "season": 2024,
                "week": week,
                "home_recent_form_known": week >= 3,
                "away_recent_form_known": week >= 3,
                "home_recent_form_weeks": min(max(week - 1, 0), 3),
                "away_recent_form_weeks": min(max(week - 1, 0), 3),
                **{
                    name: None if week < 2 else (week - 9) * 0.01
                    for name in FEATURES
                },
            }
        )
    return pl.DataFrame(rows)


def test_validate_season_measures_coverage_and_dispersion(tmp_path: Path) -> None:
    path = tmp_path / "recent.parquet"
    artifact().write_parquet(path)

    result = validate_season(path, 2024)

    assert result["rows"] == 18
    assert result["duplicate_game_ids"] == 0
    assert result["week3_plus_both_known_rate"] == 1.0
    assert result["features"][FEATURES[0]]["std"] > 0.0
    assert result["features"][FEATURES[0]]["coverage"] > 0.90


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
                "week3_plus_both_known_rate": 0.95,
                "features": {name: dict(stats) for name in FEATURES},
            }
        }
    }

    assert evaluate(report) == []


def test_evaluate_rejects_low_coverage() -> None:
    stats = {
        "coverage": 0.90,
        "std": 0.10,
        "nonzero_rate": 0.90,
    }
    report = {
        "seasons": {
            "2024": {
                "rows": 285,
                "week3_plus_both_known_rate": 0.50,
                "features": {name: dict(stats) for name in FEATURES},
            }
        }
    }

    failures = evaluate(report)
    assert any("week-3+" in failure for failure in failures)


def test_markdown_states_no_predictive_claim() -> None:
    report = {
        "seasons": {
            "2024": {
                "rows": 285,
                "both_recent_known_rate": 0.80,
                "week3_plus_both_known_rate": 0.95,
                "features": {
                    name: {
                        "coverage": 0.90,
                        "mean": 0.0,
                        "std": 0.1,
                        "p05": -0.1,
                        "median": 0.0,
                        "p95": 0.1,
                        "nonzero_rate": 0.90,
                    }
                    for name in FEATURES
                },
            }
        },
        "failures": [],
    }

    text = render_markdown(report)
    assert "does not claim predictive value" in text
    assert "does **not** promote" in text
