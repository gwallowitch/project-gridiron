"""Season orchestration pipeline for Project Gridiron."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from gridiron.data.nflverse import NFLVerseGateway
from gridiron.pgr.pipeline import run_pgr_pipeline
from gridiron.pipelines.base import PipelineRunResult
from gridiron.pipelines.features import build_team_game_feature_store
from gridiron.pipelines.play_by_play import run_play_by_play_pipeline
from gridiron.pipelines.ratings import run_team_ratings_pipeline
from gridiron.pipelines.schedules import run_schedule_pipeline
from gridiron.pipelines.strength_of_schedule import (
    run_strength_of_schedule_pipeline,
)
from gridiron.pipelines.weekly_ratings import (
    run_weekly_team_ratings_pipeline,
)
from gridiron.prediction.pipeline import run_prediction_pipeline


@dataclass(frozen=True, slots=True)
class SeasonPipelineResult:
    """Summary of a completed season pipeline."""

    season: int
    schedule: PipelineRunResult
    play_by_play: PipelineRunResult
    features: PipelineRunResult
    ratings: PipelineRunResult
    weekly_ratings: PipelineRunResult
    strength_of_schedule: PipelineRunResult
    pgr: PipelineRunResult
    predictions: PipelineRunResult
    elapsed_seconds: float


def run_season_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
    gateway: NFLVerseGateway | None = None,
) -> SeasonPipelineResult:
    """Run all current season pipelines in dependency order."""
    started_at = perf_counter()
    gateway = gateway or NFLVerseGateway()

    schedule = run_schedule_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
        gateway=gateway,
    )

    play_by_play = run_play_by_play_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
        gateway=gateway,
    )

    features = build_team_game_feature_store(
        season,
        project_root=project_root,
        database_path=database_path,
    )

    ratings = run_team_ratings_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )

    weekly_ratings = run_weekly_team_ratings_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )

    strength_of_schedule = run_strength_of_schedule_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )

    pgr = run_pgr_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )

    predictions = run_prediction_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )

    return SeasonPipelineResult(
        season=season,
        schedule=schedule,
        play_by_play=play_by_play,
        features=features,
        ratings=ratings,
        weekly_ratings=weekly_ratings,
        strength_of_schedule=strength_of_schedule,
        pgr=pgr,
        predictions=predictions,
        elapsed_seconds=perf_counter() - started_at,
    )
