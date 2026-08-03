"""Extract and aggregate raw team-rating metrics."""
from __future__ import annotations

import polars as pl

from gridiron.ratings.metrics import build_team_metrics


def test_build_team_metrics() -> None:
    feature_store = pl.DataFrame(
        {
            "team": ["A", "A", "B", "B"],
            "offensive_epa_per_play": [0.2, 0.4, 0.1, 0.3],
            "defensive_epa_per_play": [-0.2, -0.1, -0.3, -0.2],
            "offensive_success_rate": [0.50, 0.60, 0.45, 0.55],
            "defensive_success_rate": [0.35, 0.40, 0.42, 0.44],
            "yards_per_play": [6.0, 7.0, 5.5, 6.5],
            "yards_allowed_per_play": [5.0, 5.5, 5.8, 6.0],
            "turnovers": [1, 0, 2, 1],
            "takeaways": [2, 1, 1, 0],
        }
    )

    metrics = build_team_metrics(feature_store)

    assert metrics.height == 2

    team_a = metrics.filter(pl.col("team") == "A")

    assert team_a["games_played"][0] == 2
    assert abs(team_a["offensive_epa_per_play"][0] - 0.3) < 1e-9
    assert team_a["turnover_margin"][0] == 2