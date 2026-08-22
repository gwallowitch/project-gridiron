"""Materialize 2022-2025 Open-Meteo forecast research artifacts."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from urllib.error import URLError

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.weather.materializer import (
    materialize_schedule_forecasts,
    write_materialized_artifacts,
)
from gridiron.weather.open_meteo import default_fetch_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seasons",
        nargs="+",
        type=int,
        default=[2022, 2023, 2024, 2025],
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "data/curated/open_meteo_research_forecasts"
        ),
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.50,
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=8,
    )
    parser.add_argument(
        "--backoff-seconds",
        type=float,
        default=1.5,
    )
    args = parser.parse_args()

    paths = ProjectPaths.from_root(".")

    request_count = 0

    def throttled_fetch(url: str) -> dict:
        nonlocal request_count
        request_count += 1

        for attempt in range(1, args.max_retries + 1):
            try:
                payload = default_fetch_json(url)

                if args.sleep_seconds > 0:
                    time.sleep(args.sleep_seconds)

                return payload

            except (
                URLError,
                ConnectionResetError,
                TimeoutError,
                OSError,
            ) as exc:
                if attempt >= args.max_retries:
                    print(
                        f"Request {request_count} failed after "
                        f"{args.max_retries} attempts."
                    )
                    raise

                delay = min(
                    args.backoff_seconds * (2 ** (attempt - 1)),
                    30.0,
                )

                print(
                    f"Request {request_count}: "
                    f"{type(exc).__name__}: {exc}"
                )
                print(
                    f"  retry {attempt}/{args.max_retries} "
                    f"in {delay:.1f}s"
                )

                time.sleep(delay)

        raise RuntimeError("Unreachable retry state.")

    for season in args.seasons:
        schedule_path = paths.schedule_file(season)
        if not schedule_path.exists():
            raise FileNotFoundError(schedule_path)

        schedule = pl.read_parquet(schedule_path)

        print(
            f"Starting {season}: {schedule.height} games, "
            f"sleep={args.sleep_seconds}s, "
            f"max_retries={args.max_retries}"
        )

        frame, skipped = materialize_schedule_forecasts(
            schedule,
            fetch_json=throttled_fetch,
        )

        parquet_path, skipped_path = write_materialized_artifacts(
            season=season,
            frame=frame,
            skipped=skipped,
            output_dir=args.output_dir,
        )

        print(
            f"{season}: rows={frame.height} "
            f"skipped={len(skipped)} "
            f"artifact={parquet_path}"
        )

        if skipped:
            print(f"  skipped log: {skipped_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
