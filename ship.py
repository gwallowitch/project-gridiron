"""Mission control for Project Gridiron."""

from __future__ import annotations

import argparse
from time import perf_counter

from gridiron.pipelines.season import run_season_pipeline

BANNER = r"""
============================================================
                     PROJECT GRIDIRON
              Professional Football Analytics
============================================================
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ship.py",
        description="Project Gridiron Mission Control",
    )

    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="NFL season to process.",
    )

    return parser


def main() -> int:
    args = build_parser()

    started = perf_counter()

    print(BANNER)
    print(f"Launching season pipeline for {args.season}...\n")

    result = run_season_pipeline(
        season=args.season,
    )

    elapsed = perf_counter() - started

    print("Mission Complete")
    print("----------------")
    print(f"Season : {result.season}")
    print(f"Runtime: {elapsed:.2f} seconds")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())