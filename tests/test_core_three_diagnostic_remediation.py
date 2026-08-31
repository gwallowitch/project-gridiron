"""Exercise the diagnostic report end-to-end with only in-memory I/O."""

import importlib.util
import json
from pathlib import Path

import polars as pl
import pytest


def test_every_phase4c_analysis_excludes_tie(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/step91o_phase4c_2025.py"
    spec = importlib.util.spec_from_file_location("phase4c", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = [
        {
            "game_id": f"synthetic-{i}",
            "week": 2,
            "away_team": "Away",
            "home_team": "Home",
            "outcome": "HOME",
            "market_home_probability": 0.6,
            "def_epa_trend_advantage": 0.1,
            "candidate_home_probability": 0.61,
            "candidate_predicted_winner": "Home",
            "market_predicted_winner": "Home",
            "legacy_v2_home_probability": 0.6,
        }
        for i in range(255)
    ]
    # Extreme tied row would contaminate every analysis if not removed up front.
    rows.append(
        {
            **rows[0],
            "game_id": "tie-sentinel",
            "week": 18,
            "outcome": "TIE",
            "candidate_home_probability": 0.1,
            "candidate_predicted_winner": "Away",
            "def_epa_trend_advantage": -100.0,
        }
    )
    monkeypatch.setattr(module.pl, "read_csv", lambda _: pl.DataFrame(rows))
    captured = {}

    def capture(path, text, **kwargs):
        captured[path.name] = text

    monkeypatch.setattr(Path, "write_text", capture)
    module.main()
    result = json.loads(captured[module.OUT_JSON.name])
    assert result["population"]["input_rows"] == 256
    assert result["population"]["rows"] == 255
    assert all(value["n"] == 255 for value in result["overall"].values())
    for section in (
        "candidate_probability_bands",
        "market_probability_bands",
        "weekly",
    ):
        assert sum(row["n"] for row in result[section]) == 255
    assert result["candidate_vs_market"]["count"] == 0
    assert result["candidate_vs_market"]["rate"] == 0
    assert result["def_epa_adjustment"][
        "mean_absolute_probability_change"
    ] == pytest.approx(0.01)
    assert "tie-sentinel" not in json.dumps(result)


def test_phase4b_report_discloses_nonfrozen_population():
    path = Path(__file__).resolve().parents[1] / (
        "data/reports/backtests/phase4b_2025_frozen_core_three_diagnostic.json"
    )
    result = json.loads(path.read_text(encoding="utf-8"))
    assert "not frozen Weeks 1-16 replay" in result["population"]
    assert "Week 1" in result["population_boundary"]
    assert result["candidate"]["residual_cap"] == 0.0425
