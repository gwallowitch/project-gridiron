from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from gridiron.core.paths import ProjectPaths
from gridiron.experiments.models import ExperimentConfig
from gridiron.research.runner import run_research


def persist_inputs(root: Path, season: int) -> None:
    paths = ProjectPaths.from_root(root)
    paths.schedules.mkdir(parents=True, exist_ok=True)
    paths.pgr.mkdir(parents=True, exist_ok=True)
    paths.rest_features.mkdir(parents=True, exist_ok=True)

    pl.DataFrame(
        {
            "game_id": [f"{season}_g1"],
            "season": [season],
            "week": [2],
            "away_team": ["A"],
            "home_team": ["B"],
            "home_score": [24],
            "away_score": [20],
        }
    ).write_parquet(paths.schedule_file(season))

    pl.DataFrame(
        {
            "season": [season, season],
            "week": [1, 1],
            "team": ["A", "B"],
            "pgr_rating": [99.0, 101.0],
        }
    ).write_parquet(paths.pgr_file(season))

    pl.DataFrame(
        {
            "game_id": [f"{season}_g1"],
            "rest_advantage": [0],
        }
    ).write_parquet(paths.rest_features_file(season))


def experiment() -> ExperimentConfig:
    return ExperimentConfig(
        name="baseline",
        home_field_advantage=1.5,
        probability_scale=0.14,
        margin_scale=0.75,
        rest_weight=0.0,
    )


def test_runs_multiple_seasons(tmp_path: Path) -> None:
    persist_inputs(tmp_path, 2024)
    persist_inputs(tmp_path, 2025)

    run = run_research(
        profile="modern",
        seasons=(2024, 2025),
        experiments=[experiment()],
        project_root=tmp_path,
    )

    assert run.seasons == (2024, 2025)
    assert run.experiment_count == 1
    assert run.total_runs == 2
    assert len(run.results) == 2


def test_missing_season_inputs_fail_clearly(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="season 2025",
    ):
        run_research(
            profile="modern",
            seasons=(2025,),
            experiments=[experiment()],
            project_root=tmp_path,
        )
