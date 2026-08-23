from __future__ import annotations

import pytest

from gridiron.market.feature_residual_research import (
    NFLFeatureResidualObservation,
)
from gridiron.market.robustness_research import (
    run_expanding_window_feature_research,
)


def _observations() -> tuple[NFLFeatureResidualObservation, ...]:
    observations = []

    for index in range(12):
        probability = 0.65 if index % 2 == 0 else 0.35
        feature = 0.2 if index % 2 == 0 else -0.2
        outcome = 1 if index % 2 == 0 else 0

        observations.append(
            NFLFeatureResidualObservation(
                season=2022 + index // 4,
                game_id=f"{2022 + index // 4}_{index:02d}",
                market_home_probability=probability,
                feature_value=feature,
                home_win=outcome,
            )
        )

    return tuple(observations)


def test_expanding_window_creates_expected_blocks() -> None:
    results = run_expanding_window_feature_research(
        _observations(),
        minimum_train_games=6,
        test_block_games=2,
    )

    assert len(results) == 3

    assert tuple(result.train_games for result in results) == (
        6,
        8,
        10,
    )

    assert all(result.test_games == 2 for result in results)


def test_expanding_window_returns_feature_coefficients() -> None:
    results = run_expanding_window_feature_research(
        _observations(),
        minimum_train_games=6,
        test_block_games=3,
    )

    for result in results:
        assert result.market_only.games == result.test_games
        assert result.market_plus_feature.games == result.test_games
        assert isinstance(result.feature_coefficient, float)


def test_invalid_training_window_rejected() -> None:
    with pytest.raises(ValueError, match="minimum_train_games"):
        run_expanding_window_feature_research(
            _observations(),
            minimum_train_games=0,
            test_block_games=2,
        )


def test_training_window_must_leave_holdout_data() -> None:
    with pytest.raises(ValueError, match="Not enough observations"):
        run_expanding_window_feature_research(
            _observations(),
            minimum_train_games=12,
            test_block_games=2,
        )


import numpy as np

from gridiron.market.robustness_research import (
    summarize_probability_slice,
)


def test_probability_slice_reports_improvement() -> None:
    outcomes = np.array([1.0, 0.0])
    market = np.array([0.60, 0.40])
    candidate = np.array([0.70, 0.30])

    result = summarize_probability_slice(
        label="example",
        outcomes=outcomes,
        market_probabilities=market,
        candidate_probabilities=candidate,
    )

    assert result.label == "example"
    assert result.games == 2
    assert result.brier_delta < 0.0
    assert result.log_loss_delta < 0.0


def test_probability_slice_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one"):
        summarize_probability_slice(
            label="empty",
            outcomes=np.array([]),
            market_probabilities=np.array([]),
            candidate_probabilities=np.array([]),
        )


from gridiron.market.robustness_research import (
    summarize_residual_adjustments,
)


def test_residual_adjustment_summary() -> None:
    outcomes = np.array([1.0, 0.0, 1.0, 0.0])
    market = np.array([0.60, 0.40, 0.65, 0.35])
    candidate = np.array([0.64, 0.36, 0.67, 0.33])

    result = summarize_residual_adjustments(
        label="example",
        outcomes=outcomes,
        market_probabilities=market,
        candidate_probabilities=candidate,
    )

    assert result.label == "example"
    assert result.games == 4
    assert result.mean_absolute_adjustment > 0.0
    assert result.p90_absolute_adjustment >= result.p75_absolute_adjustment
    assert result.p75_absolute_adjustment >= result.p25_absolute_adjustment
    assert result.brier_delta < 0.0
    assert result.log_loss_delta < 0.0


def test_residual_adjustment_summary_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="at least one"):
        summarize_residual_adjustments(
            label="empty",
            outcomes=np.array([]),
            market_probabilities=np.array([]),
            candidate_probabilities=np.array([]),
        )


from gridiron.market.robustness_research import (
    apply_residual_cap,
    evaluate_capped_residual_probabilities,
)


def test_residual_cap_limits_probability_movement() -> None:
    market = np.array([0.60, 0.40])
    candidate = np.array([0.66, 0.33])

    capped = apply_residual_cap(
        market_probabilities=market,
        candidate_probabilities=candidate,
        cap=0.02,
    )

    assert capped[0] == pytest.approx(0.62)
    assert capped[1] == pytest.approx(0.38)


def test_uncapped_residual_returns_candidate_probabilities() -> None:
    market = np.array([0.60, 0.40])
    candidate = np.array([0.66, 0.33])

    result = apply_residual_cap(
        market_probabilities=market,
        candidate_probabilities=candidate,
        cap=None,
    )

    assert np.allclose(result, candidate)


def test_invalid_residual_cap_rejected() -> None:
    with pytest.raises(ValueError, match="cap"):
        apply_residual_cap(
            market_probabilities=np.array([0.60]),
            candidate_probabilities=np.array([0.62]),
            cap=0.0,
        )


def test_capped_residual_evaluation_returns_each_cap() -> None:
    outcomes = np.array([1, 0, 1, 0], dtype=int)
    market = np.array([0.60, 0.40, 0.65, 0.35])
    candidate = np.array([0.64, 0.36, 0.68, 0.32])

    results = evaluate_capped_residual_probabilities(
        outcomes=outcomes,
        market_probabilities=market,
        candidate_probabilities=candidate,
        caps=(0.01, 0.02, None),
    )

    assert tuple(result.cap for result in results) == (
        0.01,
        0.02,
        None,
    )
    assert all(result.games == 4 for result in results)


from gridiron.market.robustness_research import (
    NFLCappedResidualMetrics,
    NFLCapSelectionSummary,
    select_robust_residual_cap,
    summarize_cap_robustness,
)


def test_cap_robustness_summary_uses_improvement_direction() -> None:
    candidates = (
        NFLCappedResidualMetrics(0.04, 100, 0.20, 0.60),
        NFLCappedResidualMetrics(0.04, 100, 0.21, 0.62),
    )
    markets = (
        NFLCappedResidualMetrics(None, 100, 0.21, 0.62),
        NFLCappedResidualMetrics(None, 100, 0.22, 0.64),
    )

    result = summarize_cap_robustness(
        cap=0.04,
        season_metrics=candidates,
        market_metrics=markets,
    )

    assert result.mean_brier_improvement > 0.0
    assert result.worst_brier_improvement > 0.0
    assert result.mean_log_loss_improvement > 0.0
    assert result.worst_log_loss_improvement > 0.0


def test_robust_cap_selection_prefers_worst_season_brier() -> None:
    first = NFLCapSelectionSummary(
        cap=0.035,
        seasons=3,
        mean_brier_improvement=0.0010,
        worst_brier_improvement=0.0008,
        mean_log_loss_improvement=0.0020,
        worst_log_loss_improvement=0.0018,
    )
    second = NFLCapSelectionSummary(
        cap=0.040,
        seasons=3,
        mean_brier_improvement=0.0009,
        worst_brier_improvement=0.0009,
        mean_log_loss_improvement=0.0019,
        worst_log_loss_improvement=0.0017,
    )

    selected = select_robust_residual_cap((first, second))

    assert selected.cap == 0.040
