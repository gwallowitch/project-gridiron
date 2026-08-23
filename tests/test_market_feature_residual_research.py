from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.market.feature_residual_research import (
    NFLFeatureResidualObservation,
    attach_feature_to_market_observations,
    run_leave_one_season_out_feature_residual_research,
)


def test_attach_feature_zero_fills_missing_values(tmp_path: Path) -> None:
    market = pl.DataFrame(
        {
            "season": [2022, 2022],
            "game_id": ["a", "b"],
            "market_home_probability": [0.60, 0.40],
            "home_win": [1, 0],
        }
    )

    features = pl.DataFrame(
        {
            "game_id": ["a", "b"],
            "rest_advantage": [1.0, None],
        }
    )

    path = tmp_path / "features.parquet"
    features.write_parquet(path)

    observations = attach_feature_to_market_observations(
        market_frame=market,
        feature_path=path,
        feature_column="rest_advantage",
    )

    assert len(observations) == 2
    assert observations[0].feature_value == 1.0
    assert observations[1].feature_value == 0.0


def test_leave_one_season_out_feature_research_returns_three_folds() -> None:
    observations = (
        NFLFeatureResidualObservation(2022, "a", 0.70, 0.20, 1),
        NFLFeatureResidualObservation(2022, "b", 0.30, -0.10, 0),
        NFLFeatureResidualObservation(2023, "c", 0.65, 0.15, 1),
        NFLFeatureResidualObservation(2023, "d", 0.35, -0.20, 0),
        NFLFeatureResidualObservation(2024, "e", 0.75, 0.10, 1),
        NFLFeatureResidualObservation(2024, "f", 0.25, -0.15, 0),
    )

    results = run_leave_one_season_out_feature_residual_research(
        feature_name="example",
        observations=observations,
    )

    assert tuple(result.test_season for result in results) == (
        2022,
        2023,
        2024,
    )

    for result in results:
        assert result.feature_name == "example"
        assert result.market_only.games == 2
        assert result.market_plus_feature.games == 2


from gridiron.market.feature_residual_research import (
    NFLTwoFeatureResidualObservation,
    run_leave_one_season_out_two_feature_research,
)


def test_two_feature_residual_research_returns_three_folds() -> None:
    observations = (
        NFLTwoFeatureResidualObservation(2022, "a", 0.70, 0.20, 0.10, 1),
        NFLTwoFeatureResidualObservation(2022, "b", 0.30, -0.10, -0.20, 0),
        NFLTwoFeatureResidualObservation(2023, "c", 0.65, 0.15, 0.05, 1),
        NFLTwoFeatureResidualObservation(2023, "d", 0.35, -0.20, -0.10, 0),
        NFLTwoFeatureResidualObservation(2024, "e", 0.75, 0.10, 0.20, 1),
        NFLTwoFeatureResidualObservation(2024, "f", 0.25, -0.15, -0.05, 0),
    )

    results = run_leave_one_season_out_two_feature_research(observations)

    assert tuple(result.test_season for result in results) == (
        2022,
        2023,
        2024,
    )

    for result in results:
        assert result.market_only.games == 2
        assert result.market_plus_first.games == 2
        assert result.market_plus_second.games == 2
        assert result.market_plus_both.games == 2
        assert len(result.both_coefficients) == 3
