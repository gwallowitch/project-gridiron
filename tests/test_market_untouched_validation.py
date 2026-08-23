from __future__ import annotations

import numpy as np
import pytest

from gridiron.market.untouched_validation import (
    FROZEN_RESIDUAL_CAP,
    run_frozen_untouched_validation,
)


def test_frozen_cap_is_step90d_value() -> None:
    assert FROZEN_RESIDUAL_CAP == pytest.approx(0.0425)


def test_untouched_validation_returns_metrics() -> None:
    train_market = np.array(
        [0.70, 0.30, 0.65, 0.35, 0.60, 0.40]
    )
    train_epa = np.array(
        [0.10, -0.10, 0.08, -0.08, 0.05, -0.05]
    )
    train_outcomes = np.array(
        [1, 0, 1, 0, 1, 0]
    )

    test_market = np.array(
        [0.62, 0.38]
    )
    test_epa = np.array(
        [0.06, -0.06]
    )
    test_outcomes = np.array(
        [1, 0]
    )

    result = run_frozen_untouched_validation(
        train_market_probabilities=train_market,
        train_def_epa=train_epa,
        train_outcomes=train_outcomes,
        test_market_probabilities=test_market,
        test_def_epa=test_epa,
        test_outcomes=test_outcomes,
    )

    assert result.games == 2
    assert result.market_only.games == 2
    assert result.capped_residual.games == 2


def test_training_population_lengths_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="Training population lengths",
    ):
        run_frozen_untouched_validation(
            train_market_probabilities=np.array(
                [0.60, 0.40]
            ),
            train_def_epa=np.array(
                [0.10]
            ),
            train_outcomes=np.array(
                [1, 0]
            ),
            test_market_probabilities=np.array(
                [0.55]
            ),
            test_def_epa=np.array(
                [0.02]
            ),
            test_outcomes=np.array(
                [1]
            ),
        )


def test_test_population_lengths_must_match() -> None:
    with pytest.raises(
        ValueError,
        match="Test population lengths",
    ):
        run_frozen_untouched_validation(
            train_market_probabilities=np.array(
                [0.60, 0.40]
            ),
            train_def_epa=np.array(
                [0.10, -0.10]
            ),
            train_outcomes=np.array(
                [1, 0]
            ),
            test_market_probabilities=np.array(
                [0.55, 0.45]
            ),
            test_def_epa=np.array(
                [0.02]
            ),
            test_outcomes=np.array(
                [1, 0]
            ),
        )
