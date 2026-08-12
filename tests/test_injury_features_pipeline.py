from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.pipelines.injury_features import InjuryFeaturesPipeline


class Gateway:
    def injuries(self, seasons):
        return pl.DataFrame({
            "season":[2024],"game_type":["REG"],"team":["AAA"],"week":[1],
            "gsis_id":["p1"],"position":["WR"],"full_name":["Player One"],
            "first_name":["Player"],"last_name":["One"],
            "report_primary_injury":["Ankle"],"report_secondary_injury":[None],
            "report_status":["Out"],"practice_primary_injury":["Ankle"],
            "practice_secondary_injury":[None],
            "practice_status":["Did Not Participate In Practice"],
            "date_modified":[datetime(2024,9,6,tzinfo=UTC)],
        })


def test_pipeline_persists_curated_artifact(tmp_path: Path) -> None:
    paths = ProjectPaths.from_root(tmp_path)
    paths.schedules.mkdir(parents=True, exist_ok=True)
    pl.DataFrame({
        "game_id":["g1"],"season":[2024],"week":[1],
        "home_team":["AAA"],"away_team":["BBB"],
    }).write_parquet(paths.schedule_file(2024))

    result = InjuryFeaturesPipeline(
        season=2024, project_root=tmp_path, gateway=Gateway()
    ).run()

    assert result.artifact.output_path == paths.injury_features_file(2024)
    assert result.artifact.output_path.exists()
    saved = pl.read_parquet(result.artifact.output_path)
    assert saved.height == 1
