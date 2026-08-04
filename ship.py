"""Mission control for Project Gridiron."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter

from gridiron.benchmark.evaluator import evaluate_pgr_season
from gridiron.benchmark.report import print_benchmark_report
from gridiron.pipelines.season import run_season_pipeline
from gridiron.ship.banner import print_banner
from gridiron.ship.doctor import check_repository
from gridiron.ship.status import print_status


def build_parser() -> argparse.ArgumentParser:
    """Build the Mission Control command parser."""
    parser = argparse.ArgumentParser(
        prog="ship.py",
        description="Project Gridiron Mission Control",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    season = subparsers.add_parser(
        "season",
        description="Run the complete season pipeline.",
    )
    season.add_argument("--season", type=int, required=True)
    season.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )
    season.add_argument(
        "--database-path",
        type=Path,
        default=None,
    )

    doctor = subparsers.add_parser(
        "doctor",
        description="Check repository health.",
    )
    doctor.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )

    subparsers.add_parser(
        "status",
        description="Display Project Gridiron status.",
    )

    benchmark = subparsers.add_parser(
        "benchmark",
        description="Evaluate a persisted PGR season.",
    )
    benchmark.add_argument("--season", type=int, required=True)
    benchmark.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run Mission Control."""
    args = build_parser().parse_args(argv)

    print_banner()

    if args.command == "season":
        return run_season_command(
            season=args.season,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "doctor":
        return run_doctor_command(args.project_root)

    if args.command == "status":
        print_status()
        return 0

    if args.command == "benchmark":
        return run_benchmark_command(
            season=args.season,
            project_root=args.project_root,
        )

    raise RuntimeError(f"Unsupported command: {args.command}")


def run_season_command(
    *,
    season: int,
    project_root: Path,
    database_path: Path | None,
) -> int:
    """Run the complete season workflow."""
    started_at = perf_counter()

    result = run_season_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )

    elapsed = perf_counter() - started_at

    print("Mission Complete")
    print("----------------")
    print(f"Season: {result.season}")
    print("✓ Schedule")
    print("✓ Play-by-Play")
    print("✓ Team Game Features")
    print("✓ Team Ratings")
    print("✓ Weekly Team Ratings")
    print("✓ Strength of Schedule")
    print("✓ Project Gridiron Rating")
    print(f"Runtime: {elapsed:.2f} seconds")

    return 0


def run_benchmark_command(
    *,
    season: int,
    project_root: Path,
) -> int:
    """Evaluate and print the PGR benchmark for one season."""
    result = evaluate_pgr_season(
        season,
        project_root=project_root,
    )
    print_benchmark_report(result)
    return 0


def run_doctor_command(project_root: Path) -> int:
    """Run repository health checks."""
    healthy = check_repository(project_root)
    print(
        "System Status: HEALTHY"
        if healthy
        else "System Status: UNHEALTHY"
    )
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
