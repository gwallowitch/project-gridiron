"""Command-line entry points for Project Gridiron."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from gridiron.data.metadata import read_ingestion_log, record_ingestion
from gridiron.data.nflverse import NFLVerseGateway
from gridiron.data.persistence import (
    persist_play_by_play,
    persist_schedule,
)
from gridiron.pipelines.features import build_team_game_feature_store
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
    _add_persistence_arguments(schedule)

    play_by_play = subparsers.add_parser(
        "persist-play-by-play",
        description="Download and save NFL play-by-play.",
    )
    _add_persistence_arguments(play_by_play)

    features = subparsers.add_parser(
        "build-team-game-features",
        description="Build the curated team-game feature store.",
    )
    features.add_argument("--season", type=int, required=True)
    features.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )
    features.add_argument(
        "--database-path",
        type=Path,
        default=None,
    )

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


def _add_persistence_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=Path("database/gridiron.duckdb"),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "smoke-test":
        return run_smoke_test(args.season)

    if args.command == "persist-schedule":
        return run_persist_schedule(
            season=args.season,
            data_root=args.data_root,
            database_path=args.database_path,
        )

    if args.command == "persist-play-by-play":
        return run_persist_play_by_play(
            season=args.season,
            data_root=args.data_root,
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
    data_root: Path = Path("data"),
    database_path: Path = Path("database/gridiron.duckdb"),
    gateway: NFLVerseGateway | None = None,
) -> int:
    gateway = gateway or NFLVerseGateway()
    schedule = gateway.schedules([season])
    output_path = persist_schedule(
        schedule,
        season,
        data_root,
    )
    season_rows = schedule.filter(
        schedule["season"] == season
    )

    run_id = _record_file_ingestion(
        database_path=database_path,
        dataset="schedules",
        season=season,
        row_count=season_rows.height,
        column_count=len(season_rows.columns),
        output_path=output_path,
    )

    print(f"Schedule persistence completed for {season}.")
    print(f"Schedule rows: {season_rows.height}")
    print(f"Saved to: {output_path}")
    print(f"Ingestion run: {run_id}")
    return 0


def run_persist_play_by_play(
    season: int,
    data_root: Path = Path("data"),
    database_path: Path = Path("database/gridiron.duckdb"),
    gateway: NFLVerseGateway | None = None,
) -> int:
    gateway = gateway or NFLVerseGateway()
    play_by_play = gateway.play_by_play([season])
    output_path = persist_play_by_play(
        play_by_play,
        season,
        data_root,
    )
    season_rows = play_by_play.filter(
        play_by_play["season"] == season
    )

    run_id = _record_file_ingestion(
        database_path=database_path,
        dataset="play_by_play",
        season=season,
        row_count=season_rows.height,
        column_count=len(season_rows.columns),
        output_path=output_path,
    )

    print(f"Play-by-play persistence completed for {season}.")
    print(f"Play rows: {season_rows.height}")
    print(f"Columns: {len(season_rows.columns)}")
    print(f"File size: {output_path.stat().st_size:,} bytes")
    print(f"Saved to: {output_path}")
    print(f"Ingestion run: {run_id}")
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

    print(f"Team-game feature build completed for {season}.")
    print(f"Feature rows: {result.row_count}")
    print(f"Columns: {result.column_count}")
    print(f"File size: {result.file_size_bytes:,} bytes")
    print(f"Saved to: {result.output_path}")
    print(f"Ingestion run: {result.run_id}")
    return 0


def _record_file_ingestion(
    *,
    database_path: Path,
    dataset: str,
    season: int,
    row_count: int,
    column_count: int,
    output_path: Path,
) -> str:
    return record_ingestion(
        database_path=database_path,
        dataset=dataset,
        season=season,
        row_count=row_count,
        column_count=column_count,
        file_path=output_path,
        file_size_bytes=output_path.stat().st_size,
    )


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
