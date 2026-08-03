"""Season orchestration pipeline for Project Gridiron."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from gridiron.data.nflverse import NFLVerseGateway
from gridiron.pipelines.base import PipelineRunResult
from gridiron.pipelines.features import build_team_game_feature_store
from gridiron.pipelines.play_by_play import run_play_by_play_pipeline
from gridiron.pipelines.schedules import run_schedule_pipeline


@dataclass(frozen=True, slots=True)
class SeasonPipelineResult:
    """Summary of a completed season pipeline."""

    season: int
    schedule: PipelineRunResult
    play_by_play: PipelineRunResult
    features: PipelineRunResult
    elapsed_seconds: float


def run_season_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    database_path: Path | str | None = None,
    gateway: NFLVerseGateway | None = None,
) -> SeasonPipelineResult:
    """Run schedule, play-by-play, and feature pipelines in order."""
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

    return SeasonPipelineResult(
        season=season,
        schedule=schedule,
        play_by_play=play_by_play,
        features=features,
        elapsed_seconds=perf_counter() - started_at,
    )