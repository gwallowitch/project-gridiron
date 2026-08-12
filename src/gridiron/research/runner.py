"""Multi-season research orchestration."""
from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.runner import run_experiments
from gridiron.research.models import ResearchRun, SeasonResearchResult


def run_research(
    *,profile:str,seasons:tuple[int,...],
    experiments:list[ExperimentConfig],
    project_root:Path|str=Path("."),
)->ResearchRun:
    if not seasons:
        raise ValueError("Research requires at least one season.")
    if not experiments:
        raise ValueError("Research requires at least one experiment.")
    started=perf_counter()
    paths=ProjectPaths.from_root(project_root)
    results=[]
    needs_qb=any(e.qb_weight!=0.0 for e in experiments)
    needs_injury=any(e.injury_weight!=0.0 for e in experiments)

    for season in seasons:
        schedule_path=paths.schedule_file(season)
        pgr_path=paths.pgr_file(season)
        rest_path=paths.rest_features_file(season)
        qb_path=paths.qb_features_file(season)
        injury_path=paths.injury_features_file(season)
        required=[schedule_path,pgr_path,rest_path]
        if needs_qb:
            required.append(qb_path)
        if needs_injury:
            required.append(injury_path)
        missing=[p for p in required if not p.exists()]
        if missing:
            raise FileNotFoundError(
                f"Research inputs are missing for season {season}: "
                + ", ".join(str(p) for p in missing)
            )
        qb=pl.read_parquet(qb_path) if qb_path.exists() else None
        injury=(
            pl.read_parquet(injury_path)
            if injury_path.exists()
            else None
        )
        season_results=run_experiments(
            pl.read_parquet(schedule_path),
            pl.read_parquet(pgr_path),
            experiments,
            rest_features=pl.read_parquet(rest_path),
            qb_features=qb,
            injury_features=injury,
        )
        results.append(
            SeasonResearchResult(
                season=season,experiments=tuple(season_results)
            )
        )
    return ResearchRun(
        profile=profile,seasons=seasons,
        experiment_count=len(experiments),
        total_runs=len(seasons)*len(experiments),
        runtime_seconds=perf_counter()-started,
        generated_at=datetime.now(UTC).isoformat(),
        git_commit=_git_commit(paths.root),
        python_version=sys.version.split()[0],
        results=tuple(results),
    )

def _git_commit(project_root:Path)->str|None:
    try:
        completed=subprocess.run(
            ["git","rev-parse","HEAD"],cwd=project_root,check=True,
            capture_output=True,text=True
        )
    except (OSError,subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None
