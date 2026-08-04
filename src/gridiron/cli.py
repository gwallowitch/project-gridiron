"""Command-line entry points for Project Gridiron."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from gridiron.data.metadata import read_ingestion_log
from gridiron.data.nflverse import NFLVerseGateway
from gridiron.pgr.pipeline import run_pgr_pipeline
from gridiron.pipelines.base import PipelineRunResult
from gridiron.pipelines.features import build_team_game_feature_store
from gridiron.pipelines.play_by_play import run_play_by_play_pipeline
from gridiron.pipelines.ratings import run_team_ratings_pipeline
from gridiron.pipelines.schedules import run_schedule_pipeline
from gridiron.pipelines.season import run_season_pipeline
from gridiron.pipelines.strength_of_schedule import (
    run_strength_of_schedule_pipeline,
)
from gridiron.pipelines.weekly_ratings import (
    run_weekly_team_ratings_pipeline,
)
from gridiron.validation.schedules import validate_schedule


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gridiron")
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    smoke = subparsers.add_parser(
        "smoke-test",
        description="Verify access to an NFL schedule dataset.",
    )
    smoke.add_argument("--season", type=int, required=True)

    schedule = subparsers.add_parser(
        "persist-schedule",
        description="Download and save an NFL schedule.",
    )
    _add_pipeline_arguments(schedule)

    play_by_play = subparsers.add_parser(
        "persist-play-by-play",
        description="Download and save NFL play-by-play.",
    )
    _add_pipeline_arguments(play_by_play)

    features = subparsers.add_parser(
        "build-team-game-features",
        description="Build the curated team-game feature store.",
    )
    _add_pipeline_arguments(features)

    ratings = subparsers.add_parser(
        "build-team-ratings",
        description="Build the curated team-ratings dataset.",
    )
    _add_pipeline_arguments(ratings)

    weekly_ratings = subparsers.add_parser(
        "build-weekly-ratings",
        description="Build cumulative weekly team ratings.",
    )
    _add_pipeline_arguments(weekly_ratings)

    strength_of_schedule = subparsers.add_parser(
        "build-strength-of-schedule",
        description="Build weekly strength-of-schedule ratings.",
    )
    _add_pipeline_arguments(strength_of_schedule)

    pgr = subparsers.add_parser(
        "build-pgr",
        description="Build Project Gridiron Ratings.",
    )
    _add_pipeline_arguments(pgr)

    season = subparsers.add_parser(
        "run-season",
        description="Run the complete Project Gridiron season pipeline.",
    )
    _add_pipeline_arguments(season)

    history = subparsers.add_parser(
        "ingestion-history",
        description="Display recent ingestion records.",
    )
    history.add_argument(
        "--database-path",
        type=Path,
        default=Path("database/gridiron.duckdb"),
    )
    history.add_argument("--limit", type=int, default=10)

    return parser


def _add_pipeline_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=None,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "smoke-test":
        return run_smoke_test(args.season)

    if args.command == "persist-schedule":
        return run_persist_schedule(
            season=args.season,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "persist-play-by-play":
        return run_persist_play_by_play(
            season=args.season,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "build-team-game-features":
        return run_build_team_game_features(
            season=args.season,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "build-team-ratings":
        return run_build_team_ratings(
            season=args.season,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "build-weekly-ratings":
        return run_build_weekly_team_ratings(
            season=args.season,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "build-strength-of-schedule":
        return run_build_strength_of_schedule(
            season=args.season,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "build-pgr":
        return run_build_pgr(
            season=args.season,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "run-season":
        return run_complete_season(
            season=args.season,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "ingestion-history":
        return run_ingestion_history(
            database_path=args.database_path,
            limit=args.limit,
        )

    raise RuntimeError(f"Unsupported command: {args.command}")


def run_smoke_test(
    season: int,
    gateway: NFLVerseGateway | None = None,
) -> int:
    gateway = gateway or NFLVerseGateway()
    schedule = gateway.schedules([season])
    validate_schedule(schedule)

    season_rows = schedule.filter(schedule["season"] == season)

    print(f"Project Gridiron data connection passed for {season}.")
    print(f"Schedule rows: {season_rows.height}")
    print(f"Available columns: {len(schedule.columns)}")
    return 0


def run_persist_schedule(
    season: int,
    project_root: Path = Path("."),
    database_path: Path | None = None,
    gateway: NFLVerseGateway | None = None,
) -> int:
    result = run_schedule_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
        gateway=gateway,
    )
    _print_pipeline_result(label="Schedule", result=result)
    return 0


def run_persist_play_by_play(
    season: int,
    project_root: Path = Path("."),
    database_path: Path | None = None,
    gateway: NFLVerseGateway | None = None,
) -> int:
    result = run_play_by_play_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
        gateway=gateway,
    )
    _print_pipeline_result(label="Play-by-play", result=result)
    return 0


def run_build_team_game_features(
    season: int,
    project_root: Path = Path("."),
    database_path: Path | None = None,
) -> int:
    result = build_team_game_feature_store(
        season,
        project_root=project_root,
        database_path=database_path,
    )
    _print_pipeline_result(label="Team-game feature", result=result)
    return 0


def run_build_team_ratings(
    season: int,
    project_root: Path = Path("."),
    database_path: Path | None = None,
) -> int:
    result = run_team_ratings_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )
    _print_pipeline_result(label="Team ratings", result=result)
    return 0


def run_build_weekly_team_ratings(
    season: int,
    project_root: Path = Path("."),
    database_path: Path | None = None,
) -> int:
    result = run_weekly_team_ratings_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )
    _print_pipeline_result(label="Weekly team ratings", result=result)
    return 0


def run_build_strength_of_schedule(
    season: int,
    project_root: Path = Path("."),
    database_path: Path | None = None,
) -> int:
    result = run_strength_of_schedule_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )
    _print_pipeline_result(
        label="Strength of schedule",
        result=result,
    )
    return 0


def run_build_pgr(
    season: int,
    project_root: Path = Path("."),
    database_path: Path | None = None,
) -> int:
    result = run_pgr_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )
    _print_pipeline_result(label="PGR", result=result)
    return 0


def run_complete_season(
    season: int,
    project_root: Path = Path("."),
    database_path: Path | None = None,
) -> int:
    result = run_season_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )

    print()
    print("=" * 60)
    print("PROJECT GRIDIRON SEASON PIPELINE")
    print("=" * 60)
    print(f"Season: {result.season}")
    print()
    print("✓ Schedule")
    print("✓ Play-by-Play")
    print("✓ Team Game Features")
    print("✓ Team Ratings")
    print("✓ Weekly Team Ratings")
    print("✓ Strength of Schedule")
    print("✓ Project Gridiron Rating")
    print()
    print(f"Completed in {result.elapsed_seconds:.2f} seconds.")
    return 0


def _print_pipeline_result(
    *,
    label: str,
    result: PipelineRunResult,
) -> None:
    print(f"{label} pipeline completed for {result.season}.")
    print(f"Rows: {result.artifact.row_count}")
    print(f"Columns: {result.artifact.column_count}")
    print(f"File size: {result.artifact.file_size_bytes:,} bytes")
    print(f"Saved to: {result.artifact.output_path}")
    print(f"Elapsed: {result.elapsed_seconds:.3f} seconds")
    print(f"Throughput: {result.rows_per_second:,.1f} rows/second")
    print(f"Ingestion run: {result.run_id}")


def run_ingestion_history(
    database_path: Path,
    limit: int = 10,
) -> int:
    records = read_ingestion_log(database_path, limit=limit)

    if not records:
        print("No ingestion records found.")
        return 0

    for record in records:
        print(
            f"{record['imported_at']} | "
            f"{record['dataset']} | "
            f"{record['season']} | "
            f"{record['row_count']} rows | "
            f"{record['status']} | "
            f"{record['file_path']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
