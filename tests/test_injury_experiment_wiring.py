from __future__ import annotations

import math

import polars as pl
import pytest

from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.runner import run_experiments
from gridiron.experiments.validation import validate_experiments


def config(weight: float) -> ExperimentConfig:
    return ExperimentConfig(
        name=f"injury_{int(weight*100):03d}",
        home_field_advantage=1.5,
        probability_scale=0.14,
        margin_scale=0.75,
        rest_weight=0.20,
        qb_weight=0.0,
        injury_weight=weight,
    )

def test_injury_weight_defaults_to_zero() -> None:
    assert ExperimentConfig("x",1.5,0.14).injury_weight == 0.0

def test_injury_weight_must_be_finite() -> None:
    with pytest.raises(ValueError, match="injury_weight"):
        validate_experiments([ExperimentConfig("x",1.5,0.14,injury_weight=math.inf)])

def test_injury_weight_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="injury_weight"):
        validate_experiments([ExperimentConfig("x",1.5,0.14,injury_weight=-0.1)])

def test_nonzero_injury_weight_requires_features() -> None:
    schedule=pl.DataFrame({
        "game_id":["g1"],"season":[2024],"week":[1],
        "home_team":["AAA"],"away_team":["BBB"],
        "home_score":[20],"away_score":[10],
    })
    pgr=pl.DataFrame({
        "season":[2024,2024],"week":[0,0],
        "team":["AAA","BBB"],"pgr":[100.0,100.0],
    })
    rest = pl.DataFrame(
        {
            "game_id": ["g1"],
            "rest_advantage": [0.0],
        }
    )

    with pytest.raises(
        ValueError,
        match="Injury features are required",
    ):
        run_experiments(
            schedule,
            pgr,
            [config(0.1)],
            rest_features=rest,
        )

def test_timestamp_unavailable_injury_features_rejected() -> None:
    schedule=pl.DataFrame({
        "game_id":["g1"],"season":[2024],"week":[1],
        "home_team":["AAA"],"away_team":["BBB"],
        "home_score":[20],"away_score":[10],
    })
    pgr=pl.DataFrame({
        "season":[2024,2024],"week":[0,0],
        "team":["AAA","BBB"],"pgr":[100.0,100.0],
    })
    rest=pl.DataFrame({"game_id":["g1"],"rest_advantage":[0.0]})
    injury=pl.DataFrame({
        "game_id":["g1"],
        "injury_score_difference":[1.0],
        "source_timestamp_available":[False],
    })
    with pytest.raises(ValueError, match="timestamp-available"):
        run_experiments(
            schedule,pgr,[config(0.1)],
            rest_features=rest,injury_features=injury,
        )
