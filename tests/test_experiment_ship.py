from __future__ import annotations

import ship


def test_ship_parser_accepts_experiment_command() -> None:
    args = ship.build_parser().parse_args(
        ["experiment", "--season", "2025"]
    )

    assert args.command == "experiment"
    assert args.season == 2025
    assert args.config is None
