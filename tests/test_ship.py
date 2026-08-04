from __future__ import annotations

from pathlib import Path

import ship


def test_ship_parser_accepts_season_command() -> None:
    args = ship.build_parser().parse_args(
        ["season", "--season", "2025"]
    )

    assert args.command == "season"
    assert args.season == 2025
    assert args.project_root == Path(".")
    assert args.database_path is None


def test_ship_parser_accepts_doctor_command() -> None:
    args = ship.build_parser().parse_args(["doctor"])

    assert args.command == "doctor"
    assert args.project_root == Path(".")


def test_ship_parser_accepts_benchmark_command() -> None:
    args = ship.build_parser().parse_args(
        ["benchmark", "--season", "2025"]
    )

    assert args.command == "benchmark"
    assert args.season == 2025
    assert args.project_root == Path(".")


def test_ship_parser_accepts_status_command() -> None:
    args = ship.build_parser().parse_args(["status"])

    assert args.command == "status"


def test_doctor_returns_zero_for_healthy_repository(
    tmp_path: Path,
) -> None:
    for directory in (
        "data",
        "database",
        "docs",
        "src",
        "tests",
    ):
        (tmp_path / directory).mkdir()

    assert ship.run_doctor_command(tmp_path) == 0


def test_doctor_returns_one_for_unhealthy_repository(
    tmp_path: Path,
) -> None:
    assert ship.run_doctor_command(tmp_path) == 1