from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.data.metadata import read_ingestion_log
from gridiron.pipelines.season import run_season_pipeline


class FakeGateway:
    def schedules(self, seasons: list[int]) -> pl.DataFrame:
        season = seasons[0]

        return pl.DataFrame(
            {
                "game_id": [f"{season}_01_A_B"],
                "season": [season],
                "week": [1],
                "game_type": ["REG"],
                "gameday": [f"{season}-09-01"],
                "away_team": ["A"],
                "home_team": ["B"],
            }
        )

    def play_by_play(self, seasons: list[int]) -> pl.DataFrame:
        season = seasons[0]

        return pl.DataFrame(
            {
                "play_id": [1, 2, 3, 4, 5, 6],
                "game_id": [f"{season}_01_A_B"] * 6,
                "season": [season] * 6,
                "week": [1] * 6,
                "posteam": ["A", "A", "B", "B", "C", "C"],
                "defteam": ["B", "B", "A", "A", "A", "A"],
                "play_type": [
                    "run",
                    "pass",
                    "run",
                    "pass",
                    "run",
                    "pass",
                ],
                "epa": [0.5, -0.2, 0.8, -0.1, -0.4, -0.3],
                "success": [1.0, 0.0, 1.0, 0.0, 0.0, 0.0],
                "yards_gained": [8.0, 3.0, 12.0, 4.0, 2.0, 1.0],
                "pass_attempt": [0.0, 1.0, 0.0, 1.0, 0.0, 1.0],
                "rush_attempt": [1.0, 0.0, 1.0, 0.0, 1.0, 0.0],
                "interception": [0.0] * 6,
                "fumble_lost": [0.0] * 6,
            }
        )


def test_run_season_pipeline_completes_all_stages(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    result = run_season_pipeline(
        2025,
        project_root=tmp_path,
        database_path=paths.metadata_database,
        gateway=FakeGateway(),
    )

    assert result.season == 2025
    assert result.schedule.run_id
    assert result.play_by_play.run_id
    assert result.features.run_id
    assert result.ratings.run_id
    assert result.elapsed_seconds >= 0
    assert result.weekly_ratings.run_id
    assert result.strength_of_schedule.run_id
    assert result.pgr.run_id
    assert paths.weekly_team_ratings_file(2025).exists()
    assert paths.strength_of_schedule_file(2025).exists()
    assert paths.pgr_file(2025).exists()

    assert paths.schedule_file(2025).exists()
    assert paths.play_by_play_file(2025).exists()
    assert paths.team_game_features_file(2025).exists()
    assert paths.team_ratings_file(2025).exists()

    records = read_ingestion_log(paths.metadata_database)

    assert len(records) == 7
    assert {record["dataset"] for record in records} == {
        "schedules",
        "play_by_play",
        "team_game_features",
        "team_ratings",
        "weekly_team_ratings",
        "strength_of_schedule",
        "pgr",
    }