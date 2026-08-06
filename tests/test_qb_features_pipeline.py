from __future__ import annotations

from pathlib import Path

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.pipelines.qb_features import (
    run_qb_features_pipeline,
)


def test_pipeline_persists_neutral_defaults(
    tmp_path: Path,
) -> None:
    paths = ProjectPaths.from_root(tmp_path)
    paths.schedules.mkdir(parents=True, exist_ok=True)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)

    pl.DataFrame(
        {
            "game_id": ["g1"],
            "season": [2025],
            "week": [1],
            "home_team": ["AAA"],
            "away_team": ["BBB"],
        }
    ).write_parquet(paths.schedule_file(2025))

    result = run_qb_features_pipeline(
        2025,
        project_root=tmp_path,
    )

    assert result.artifact.output_path.exists()
    saved = pl.read_parquet(result.artifact.output_path)
    assert saved["qb_rating_difference"].to_list() == [0.0]
