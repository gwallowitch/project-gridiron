"""Mission control for Project Gridiron."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from time import perf_counter

import polars as pl

from gridiron.backtest.pipeline import run_backtest_pipeline
from gridiron.backtest.report import print_backtest_report
from gridiron.benchmark.evaluator import evaluate_pgr_season
from gridiron.benchmark.report import print_benchmark_report
from gridiron.core.paths import ProjectPaths
from gridiron.experiments.config import load_experiments
from gridiron.experiments.registry import append_registry
from gridiron.experiments.report import print_experiment_report
from gridiron.experiments.runner import run_experiments
from gridiron.pipelines.season import run_season_pipeline
from gridiron.prediction.pipeline import run_prediction_pipeline
from gridiron.prediction.report import print_prediction_report
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

    predict = subparsers.add_parser(
        "predict",
        description="Build and display predictions for one week.",
    )
    predict.add_argument("--season", type=int, required=True)
    predict.add_argument("--week", type=int, required=True)
    predict.add_argument("--project-root", type=Path, default=Path("."))
    predict.add_argument("--database-path", type=Path, default=None)

    backtest = subparsers.add_parser(
        "backtest",
        description="Evaluate historical predictions against completed games.",
    )
    backtest.add_argument("--season", type=int, required=True)
    backtest.add_argument("--project-root", type=Path, default=Path("."))
    backtest.add_argument("--database-path", type=Path, default=None)

    experiment = subparsers.add_parser(
        "experiment",
        description="Run and rank prediction parameter experiments.",
    )
    experiment.add_argument("--season", type=int, required=True)
    experiment.add_argument("--project-root", type=Path, default=Path("."))
    experiment.add_argument("--config", type=Path, default=None)

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

    if args.command == "predict":
        return run_predict_command(
            season=args.season,
            week=args.week,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "backtest":
        return run_backtest_command(
            season=args.season,
            project_root=args.project_root,
            database_path=args.database_path,
        )

    if args.command == "experiment":
        return run_experiment_command(
            season=args.season,
            project_root=args.project_root,
            config_path=args.config,
        )

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
    print("✓ Predictions")
    print(f"Runtime: {elapsed:.2f} seconds")

    return 0


def run_predict_command(
    *,
    season: int,
    week: int,
    project_root: Path,
    database_path: Path | None,
) -> int:
    run_prediction_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )
    paths = ProjectPaths.from_root(project_root)
    predictions = pl.read_parquet(paths.predictions_file(season))
    print_prediction_report(predictions, week=week)
    return 0


def run_backtest_command(
    *,
    season: int,
    project_root: Path,
    database_path: Path | None,
) -> int:
    """Run and print a historical prediction backtest."""
    _, result = run_backtest_pipeline(
        season,
        project_root=project_root,
        database_path=database_path,
    )
    print_backtest_report(result)
    return 0


def run_experiment_command(
    *,
    season: int,
    project_root: Path,
    config_path: Path | None,
) -> int:
    """Run configured prediction experiments and persist the registry."""
    paths = ProjectPaths.from_root(project_root)
    resolved_config = (
        config_path
        if config_path is not None
        else paths.root / "config" / "experiments.toml"
    )
    experiments = load_experiments(resolved_config)
    schedule = pl.read_parquet(paths.schedule_file(season))
    pgr = pl.read_parquet(paths.pgr_file(season))
    results = run_experiments(schedule, pgr, experiments)
    registry_path = (
        paths.root
        / "data"
        / "reports"
        / "experiments"
        / "experiment_registry.json"
    )
    append_registry(registry_path, results)
    print_experiment_report(results)
    print(f"Registry: {registry_path}")
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
