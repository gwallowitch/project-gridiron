from __future__ import annotations

from pathlib import Path

import ship


def test_ship_parser_accepts_backtest_command() -> None:
    args = ship.build_parser().parse_args(
        ["backtest", "--season", "2025"]
    )
    assert args.command == "backtest"
    assert args.season == 2025
    assert args.project_root == Path(".")
    assert args.database_path is None
