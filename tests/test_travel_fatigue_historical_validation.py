from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl

SCRIPT = Path("scripts/validate_travel_fatigue_history.py")
SPEC = importlib.util.spec_from_file_location(
    "validate_travel_fatigue_history",
    SCRIPT,
)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_evaluate_accepts_healthy_travel_report() -> None:
    report = {
        "seasons": {
            "2025": {
                "rows": 285,
                "schedule_rows": 285,
                "geography_known_rate": 1.0,
                "rest_known_rate": 1.0,
                "features": {
                    "away_travel_miles": {
                        "std": 700.0,
                        "p95": 2200.0,
                    },
                    "away_time_zone_shift_hours": {
                        "std": 0.8,
                    },
                },
                "flags": {
                    "long_haul_travel": {"rate": 0.25},
                    "cross_country_travel": {"rate": 0.10},
                },
                "site_audit": {
                    "neutral_count": 0,
                    "international_count": 0,
                },
            }
        }
    }

    failures, warnings = MODULE.evaluate(report)

    assert failures == []
    assert warnings == []


def test_low_geography_coverage_fails() -> None:
    report = {
        "seasons": {
            "2025": {
                "rows": 285,
                "schedule_rows": 285,
                "geography_known_rate": 0.90,
                "rest_known_rate": 1.0,
                "features": {
                    "away_travel_miles": {
                        "std": 700.0,
                        "p95": 2200.0,
                    },
                    "away_time_zone_shift_hours": {
                        "std": 0.8,
                    },
                },
                "flags": {
                    "long_haul_travel": {"rate": 0.25},
                    "cross_country_travel": {"rate": 0.10},
                },
                "site_audit": {
                    "neutral_count": 0,
                    "international_count": 0,
                },
            }
        }
    }

    failures, _ = MODULE.evaluate(report)

    assert any("geography coverage" in item for item in failures)


def test_site_audit_detects_neutral_and_london() -> None:
    schedule = pl.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2025, 2025],
            "week": [5, 6],
            "away_team": ["NYJ", "JAX"],
            "home_team": ["MIN", "NE"],
            "neutral_site": [True, False],
            "stadium": ["Tottenham Hotspur Stadium", "Gillette Stadium"],
        }
    )

    audit = MODULE._neutral_audit(schedule)

    assert audit["neutral_count"] == 1
    assert audit["international_count"] == 1


def test_markdown_disclaims_predictive_value() -> None:
    report = {
        "seasons": {},
        "failures": [],
        "warnings": [],
    }

    text = MODULE.render_markdown(report)

    assert "does not claim predictive value" in text
