"""Command-line entry points for Project Gridiron."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from gridiron.data.metadata import read_ingestion_log
from gridiron.data.nflverse import NFLVerseGateway
from gridiron.pipelines.features import build_team_game_feature_store
from gridiron.pipelines.play_by_play import (
    run_play_by_play_pipeline,
)
from gridiron.pipelines.schedules import run_schedule_pipeline
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

    season_rows = schedule.filter(
        schedule["season"] == season
    )

    print(
        f"Project Gridiron data connection passed for {season}."
    )
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

    _print_pipeline_result(
        label="Schedule",
        result=result,
    )
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

    _print_pipeline_result(
        label="Play-by-play",
        result=result,
    )
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

    _print_pipeline_result(
        label="Team-game feature",
        result=result,
    )
    return 0


def _print_pipeline_result(
    *,
    label: str,
    result: object,
) -> None:
    print(f"{label} pipeline completed for {result.season}.")
    print(f"Rows: {result.artifact.row_count}")
    print(f"Columns: {result.artifact.column_count}")
    print(
        f"File size: "
        f"{result.artifact.file_size_bytes:,} bytes"
    )
    print(f"Saved to: {result.artifact.output_path}")
    print(f"Elapsed: {result.elapsed_seconds:.3f} seconds")
    print(
        f"Throughput: "
        f"{result.rows_per_second:,.1f} rows/second"
    )
    print(f"Ingestion run: {result.run_id}")


def run_ingestion_history(
    database_path: Path,
    limit: int = 10,
) -> int:
    records = read_ingestion_log(
        database_path,
        limit=limit,
    )

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
