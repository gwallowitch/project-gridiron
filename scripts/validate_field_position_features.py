"""Historical validation report for field-position feature artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

SEASONS = (2022, 2023, 2024, 2025)

FEATURE_COLUMNS = (
    "off_start_field_position_advantage",
    "def_field_position_advantage",
    "short_field_rate_difference",
    "long_field_avoidance_advantage",
    "hidden_yards_field_position_advantage",
)

COVERAGE_COLUMNS = (
    "home_field_position_known",
    "away_field_position_known",
)

SAMPLE_COLUMNS = (
    "home_off_drives_started",
    "away_off_drives_started",
    "home_def_opponent_drives_started",
    "away_def_opponent_drives_started",
    "home_field_position_history_weeks",
    "away_field_position_history_weeks",
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
        / "field_position_features"
        / f"field_position_features_{season}.parquet"
    )


def validate_season(path: Path, season: int) -> SeasonValidation:
    if not path.exists():
        raise FileNotFoundError(f"Missing field-position artifact: {path}")

    frame = pl.read_parquet(path)

    required = {
        "game_id",
        "season",
        *COVERAGE_COLUMNS,
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

    seasons = frame["season"].drop_nulls().unique().to_list()
    if seasons != [season]:
        raise ValueError(
            f"{season} artifact has unexpected season values: {seasons}"
        )

    home_known = float(frame["home_field_position_known"].mean())
    away_known = float(frame["away_field_position_known"].mean())

    coverage = {
        column: float(frame[column].is_not_null().mean())
        for column in FEATURE_COLUMNS
    }
    means = {
        column: _mean(frame, column)
        for column in FEATURE_COLUMNS
    }
    stds = {
        column: _std(frame, column)
        for column in FEATURE_COLUMNS
    }
    sample_means = {
        column: _mean(frame, column)
        for column in SAMPLE_COLUMNS
    }

    return SeasonValidation(
        season=season,
        rows=frame.height,
        home_known=home_known,
        away_known=away_known,
        feature_coverage=coverage,
        feature_mean=means,
        feature_std=stds,
        sample_means=sample_means,
    )


def _mean(frame: pl.DataFrame, column: str) -> float | None:
    value = frame[column].mean()
    return None if value is None else float(value)


def _std(frame: pl.DataFrame, column: str) -> float | None:
    value = frame[column].std()
    return None if value is None else float(value)


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
        if result.home_known < 0.90 or result.away_known < 0.90:
            raise ValueError(
                f"{result.season} field-position known coverage is below 90%."
            )

        for column, coverage in result.feature_coverage.items():
            if coverage < 0.85:
                raise ValueError(
                    f"{result.season} {column} coverage is below 85%."
                )

        history = result.sample_means["home_field_position_history_weeks"]
        if history is None or history < 5.0:
            raise ValueError(
                f"{result.season} field-position history depth is unexpectedly low."
            )

        drives = result.sample_means["home_off_drives_started"]
        if drives is None or drives < 40.0:
            raise ValueError(
                f"{result.season} offensive drive-start sample depth is too low."
            )

        opponent_drives = result.sample_means["home_def_opponent_drives_started"]
        if opponent_drives is None or opponent_drives < 40.0:
            raise ValueError(
                f"{result.season} defensive drive-start sample depth is too low."
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
        "=" * 96,
        "PROJECT GRIDIRON — FIELD POSITION HISTORICAL VALIDATION",
        "=" * 96,
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
            lines.append(f"  {column:<42} {coverage:.1%}")

        lines.append("Feature means / std:")
        for column in FEATURE_COLUMNS:
            mean = result.feature_mean[column]
            std = result.feature_std[column]
            lines.append(
                f"  {column:<42} mean={mean: .4f}  std={std: .4f}"
            )

        lines.append("Sample depth means:")
        for column, value in result.sample_means.items():
            lines.append(f"  {column:<42} {value:.2f}")
        lines.append("-" * 96)

    lines.append("STATUS: PASS")
    lines.append("=" * 96)
    return "\n".join(lines)


def main() -> int:
    results = validate_history(Path("."))
    print(format_report(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
