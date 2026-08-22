from __future__ import annotations

import math

import polars as pl
import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.runner import run_experiments
from gridiron.experiments.validation import validate_experiments


def config(**kwargs) -> ExperimentConfig:
    values = {
        "name": "turnover_test",
        "home_field_advantage": 1.5,
        "probability_scale": 0.14,
        "margin_scale": 0.75,
        "rest_weight": 0.0,
        "qb_weight": 0.0,
        "injury_weight": 0.0,
        "early_down_off_weight": 0.0,
        "early_down_def_weight": 0.0,
        "early_down_success_weight": 0.0,
        "turnover_int_weight": 0.0,
        "turnover_fumble_weight": 0.0,
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


def turnover(known: bool = True) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "game_id": ["g1"],
            "interception_rate_difference": [0.50],
            "fumble_lost_rate_difference": [0.25],
            "home_turnover_known": [known],
            "away_turnover_known": [known],
        }
    )


def test_turnover_weights_default_to_zero() -> None:
    x = ExperimentConfig("x", 1.5, 0.14)
    assert x.turnover_int_weight == 0.0
    assert x.turnover_fumble_weight == 0.0


def test_turnover_weights_must_be_finite() -> None:
    with pytest.raises(ValueError, match="turnover_int_weight"):
        validate_experiments(
            [config(turnover_int_weight=math.inf)]
        )


def test_nonzero_turnover_weight_requires_features() -> None:
    with pytest.raises(
        ValueError,
        match="Turnover features are required",
    ):
        run_experiments(
            schedule(),
            pgr(),
            [config(turnover_int_weight=1.0)],
        )


def test_unknown_turnover_rows_are_neutral_filled() -> None:
    result = run_experiments(
        schedule(),
        pgr(),
        [config(turnover_int_weight=10.0)],
        turnover_features=turnover(known=False),
    )
    assert result[0].games_evaluated == 1


def test_known_turnover_features_can_run() -> None:
    result = run_experiments(
        schedule(),
        pgr(),
        [
            config(
                turnover_int_weight=1.0,
                turnover_fumble_weight=1.0,
            )
        ],
        turnover_features=turnover(),
    )
    assert result[0].games_evaluated == 1
