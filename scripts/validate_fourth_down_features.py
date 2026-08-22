"""Historical validation report for fourth-down feature artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

SEASONS = (2022, 2023, 2024, 2025)

FEATURE_COLUMNS = (
    "fourth_down_off_epa_difference",
    "fourth_down_def_epa_difference",
    "fourth_down_conversion_difference",
    "fourth_down_stop_difference",
    "fourth_short_conversion_difference",
)

SAMPLE_COLUMNS = (
    "home_off_fourth_down_attempts",
    "away_off_fourth_down_attempts",
    "home_def_fourth_down_attempts_faced",
    "away_def_fourth_down_attempts_faced",
    "home_off_fourth_short_attempts",
    "away_off_fourth_short_attempts",
    "home_fourth_down_history_weeks",
    "away_fourth_down_history_weeks",
)


@dataclass(frozen=True, slots=True)
class SeasonValidation:
    season: int
    rows: int
    home_known: float
    away_known: float
    feature_coverage: dict[str, float]
    feature_mean: dict[str, float | None]
    feature_std: dict[str, float | None]
    sample_means: dict[str, float | None]


def artifact_path(project_root: Path, season: int) -> Path:
    return (
        project_root
        / "data"
        / "curated"
        / "fourth_down_features"
        / f"fourth_down_features_{season}.parquet"
    )


def _mean(frame: pl.DataFrame, column: str) -> float | None:
    value = frame[column].mean()
    return None if value is None else float(value)


def _std(frame: pl.DataFrame, column: str) -> float | None:
    value = frame[column].std()
    return None if value is None else float(value)


def validate_season(path: Path, season: int) -> SeasonValidation:
    if not path.exists():
        raise FileNotFoundError(f"Missing fourth-down artifact: {path}")

    frame = pl.read_parquet(path)

    required = {
        "game_id",
        "season",
        "home_fourth_down_known",
        "away_fourth_down_known",
        *FEATURE_COLUMNS,
        *SAMPLE_COLUMNS,
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{season} artifact is missing columns: "
            + ", ".join(sorted(missing))
        )

    if frame["game_id"].n_unique() != frame.height:
        raise ValueError(
            f"{season} artifact contains duplicate game_id values."
        )

    seasons = sorted(frame["season"].drop_nulls().unique().to_list())
    if seasons != [season]:
        raise ValueError(
            f"{season} artifact has unexpected season values: {seasons}"
        )

    return SeasonValidation(
        season=season,
        rows=frame.height,
        home_known=float(frame["home_fourth_down_known"].mean()),
        away_known=float(frame["away_fourth_down_known"].mean()),
        feature_coverage={
            column: float(frame[column].is_not_null().mean())
            for column in FEATURE_COLUMNS
        },
        feature_mean={
            column: _mean(frame, column)
            for column in FEATURE_COLUMNS
        },
        feature_std={
            column: _std(frame, column)
            for column in FEATURE_COLUMNS
        },
        sample_means={
            column: _mean(frame, column)
            for column in SAMPLE_COLUMNS
        },
    )


def validate_history(
    project_root: Path = Path("."),
    seasons: tuple[int, ...] = SEASONS,
) -> list[SeasonValidation]:
    results = [
        validate_season(artifact_path(project_root, season), season)
        for season in seasons
    ]
    _validate_cross_season(results)
    return results


def _validate_cross_season(results: list[SeasonValidation]) -> None:
    if not results:
        raise ValueError("At least one season is required.")

    for result in results:
        # Fourth down is sparse by nature. Known-history coverage should still
        # be very high after Week 1, but derived short-yardage features can be
        # less complete than generic fourth-down features.
        if result.home_known < 0.90 or result.away_known < 0.90:
            raise ValueError(
                f"{result.season} fourth-down known coverage is below 90%."
            )

        for column, coverage in result.feature_coverage.items():
            minimum = (
                0.70
                if column == "fourth_short_conversion_difference"
                else 0.85
            )
            if coverage < minimum:
                raise ValueError(
                    f"{result.season} {column} coverage is below "
                    f"{minimum:.0%}."
                )

        history = result.sample_means["home_fourth_down_history_weeks"]
        if history is None or history < 4.0:
            raise ValueError(
                f"{result.season} fourth-down history depth is unexpectedly low."
            )

        attempts = result.sample_means["home_off_fourth_down_attempts"]
        if attempts is None or attempts < 4.0:
            raise ValueError(
                f"{result.season} offensive fourth-down sample depth is too low."
            )

        faced = result.sample_means["home_def_fourth_down_attempts_faced"]
        if faced is None or faced < 4.0:
            raise ValueError(
                f"{result.season} defensive fourth-down sample depth is too low."
            )

        for column, mean in result.feature_mean.items():
            if mean is None:
                raise ValueError(
                    f"{result.season} {column} has no usable observations."
                )

        for column, std in result.feature_std.items():
            if std is None or std <= 0.0:
                raise ValueError(
                    f"{result.season} {column} has no dispersion."
                )


def format_report(results: list[SeasonValidation]) -> str:
    lines = [
        "=" * 100,
        "PROJECT GRIDIRON — FOURTH-DOWN HISTORICAL VALIDATION",
        "=" * 100,
    ]

    for result in results:
        lines.extend(
            [
                f"Season {result.season}",
                f"Rows...................... {result.rows}",
                f"Home known................ {result.home_known:.1%}",
                f"Away known................ {result.away_known:.1%}",
                "Feature coverage:",
            ]
        )

        for column, coverage in result.feature_coverage.items():
            lines.append(f"  {column:<46} {coverage:.1%}")

        lines.append("Feature means / std:")
        for column in FEATURE_COLUMNS:
            mean = result.feature_mean[column]
            std = result.feature_std[column]
            lines.append(
                f"  {column:<46} mean={mean: .4f}  std={std: .4f}"
            )

        lines.append("Sample depth means:")
        for column, value in result.sample_means.items():
            lines.append(f"  {column:<46} {value:.2f}")

        lines.append("-" * 100)

    lines.append("STATUS: PASS")
    lines.append("=" * 100)
    return "\n".join(lines)


def main() -> int:
    results = validate_history(Path("."))
    print(format_report(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
