from __future__ import annotations

import math

import polars as pl
import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.runner import run_experiments
from gridiron.experiments.validation import validate_experiments


def base_config(**kwargs) -> ExperimentConfig:
    values = {
        "name": "early_down_test",
        "home_field_advantage": 1.5,
        "probability_scale": 0.14,
        "margin_scale": 0.75,
        "rest_weight": 0.0,
        "qb_weight": 0.0,
        "injury_weight": 0.0,
        "early_down_off_weight": 0.0,
        "early_down_def_weight": 0.0,
        "early_down_success_weight": 0.0,
    }
    values.update(kwargs)
    return ExperimentConfig(**values)


def schedule() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2024],
            "week": [2],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
            "home_score": [24],
            "away_score": [17],
        }
    )


def pgr() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2024, 2024],
            "week": [1, 1],
            "team": ["AAA", "BBB"],
            "pgr_rating": [100.0, 100.0],
        }
    )


def early_down(known: bool = True) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "early_down_off_epa_difference": [0.20],
            "early_down_def_epa_difference": [0.10],
            "early_down_success_difference": [0.05],
            "home_early_down_known": [known],
            "away_early_down_known": [known],
        }
    )


def test_early_down_weights_default_to_zero() -> None:
    config = ExperimentConfig("x", 1.5, 0.14)
    assert config.early_down_off_weight == 0.0
    assert config.early_down_def_weight == 0.0
    assert config.early_down_success_weight == 0.0


def test_early_down_weights_must_be_finite() -> None:
    with pytest.raises(ValueError, match="early_down_off_weight"):
        validate_experiments(
            [base_config(early_down_off_weight=math.inf)]
        )


def test_nonzero_early_down_weight_requires_features() -> None:
    with pytest.raises(ValueError, match="Early-down features are required"):
        run_experiments(
            schedule(),
            pgr(),
            [base_config(early_down_off_weight=1.0)],
        )


def test_unknown_early_down_rows_are_neutral_filled() -> None:
    result = run_experiments(
        schedule(),
        pgr(),
        [base_config(early_down_off_weight=10.0)],
        early_down_features=early_down(known=False),
    )
    assert result[0].games_evaluated == 1


def test_known_early_down_features_can_run() -> None:
    result = run_experiments(
        schedule(),
        pgr(),
        [
            base_config(
                early_down_off_weight=1.0,
                early_down_def_weight=1.0,
                early_down_success_weight=1.0,
            )
        ],
        early_down_features=early_down(),
    )
    assert result[0].games_evaluated == 1
