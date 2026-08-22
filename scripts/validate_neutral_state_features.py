"""Historical validation report for neutral-state feature artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

SEASONS = (2022, 2023, 2024, 2025)

FEATURE_COLUMNS = (
    "neutral_off_epa_difference",
    "neutral_def_epa_difference",
    "neutral_success_difference",
    "neutral_yards_per_play_difference",
    "neutral_explosive_rate_difference",
)

COVERAGE_COLUMNS = (
    "home_neutral_state_known",
    "away_neutral_state_known",
)

SAMPLE_COLUMNS = (
    "home_off_neutral_plays",
    "away_off_neutral_plays",
    "home_def_neutral_plays",
    "away_def_neutral_plays",
    "home_neutral_state_history_weeks",
    "away_neutral_state_history_weeks",
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
        / "neutral_state_features"
        / f"neutral_state_features_{season}.parquet"
    )


def validate_season(path: Path, season: int) -> SeasonValidation:
    if not path.exists():
        raise FileNotFoundError(f"Missing neutral-state artifact: {path}")

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

    home_known = float(frame["home_neutral_state_known"].mean())
    away_known = float(frame["away_neutral_state_known"].mean())

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
                f"{result.season} neutral-state known coverage is below 90%."
            )

        for column, coverage in result.feature_coverage.items():
            if coverage < 0.85:
                raise ValueError(
                    f"{result.season} {column} coverage is below 85%."
                )

        history = result.sample_means["home_neutral_state_history_weeks"]
        if history is None or history < 5.0:
            raise ValueError(
                f"{result.season} neutral-state history depth is unexpectedly low."
            )

        plays = result.sample_means["home_off_neutral_plays"]
        if plays is None or plays < 75.0:
            raise ValueError(
                f"{result.season} neutral-state offensive sample depth is too low."
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
        "PROJECT GRIDIRON — NEUTRAL GAME-STATE HISTORICAL VALIDATION",
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
