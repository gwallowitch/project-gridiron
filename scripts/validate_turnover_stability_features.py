"""Historical validation report for turnover-stability feature artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

SEASONS = (2022, 2023, 2024, 2025)

SKILL_FEATURE_COLUMNS = (
    "turnover_protection_advantage",
    "takeaway_creation_advantage",
    "interception_protection_advantage",
    "interception_creation_advantage",
)

LUCK_FEATURE_COLUMNS = (
    "off_fumble_luck_advantage",
    "def_fumble_luck_advantage",
    "combined_fumble_recovery_luck",
)

FEATURE_COLUMNS = SKILL_FEATURE_COLUMNS + LUCK_FEATURE_COLUMNS

SAMPLE_COLUMNS = (
    "home_off_turnover_eligible_plays",
    "away_off_turnover_eligible_plays",
    "home_def_turnover_eligible_plays_faced",
    "away_def_turnover_eligible_plays_faced",
    "home_off_fumbles",
    "away_off_fumbles",
    "home_def_opponent_fumbles",
    "away_def_opponent_fumbles",
    "home_turnover_stability_history_weeks",
    "away_turnover_stability_history_weeks",
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
        / "turnover_stability_features"
        / f"turnover_stability_features_{season}.parquet"
    )


def _mean(frame: pl.DataFrame, column: str) -> float | None:
    value = frame[column].mean()
    return None if value is None else float(value)


def _std(frame: pl.DataFrame, column: str) -> float | None:
    value = frame[column].std()
    return None if value is None else float(value)


def validate_season(path: Path, season: int) -> SeasonValidation:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing turnover-stability artifact: {path}"
        )

    frame = pl.read_parquet(path)

    required = {
        "game_id",
        "season",
        "home_turnover_stability_known",
        "away_turnover_stability_known",
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
        home_known=float(
            frame["home_turnover_stability_known"].mean()
        ),
        away_known=float(
            frame["away_turnover_stability_known"].mean()
        ),
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


def _validate_cross_season(
    results: list[SeasonValidation],
) -> None:
    if not results:
        raise ValueError("At least one season is required.")

    for result in results:
        if result.home_known < 0.90 or result.away_known < 0.90:
            raise ValueError(
                f"{result.season} turnover-stability known coverage "
                "is below 90%."
            )

        for column in SKILL_FEATURE_COLUMNS:
            coverage = result.feature_coverage[column]
            if coverage < 0.85:
                raise ValueError(
                    f"{result.season} {column} coverage is below 85%."
                )

        for column in LUCK_FEATURE_COLUMNS:
            coverage = result.feature_coverage[column]
            if coverage < 0.65:
                raise ValueError(
                    f"{result.season} {column} coverage is below 65%."
                )

        history = result.sample_means[
            "home_turnover_stability_history_weeks"
        ]
        if history is None or history < 5.0:
            raise ValueError(
                f"{result.season} turnover-stability history depth "
                "is unexpectedly low."
            )

        off_plays = result.sample_means[
            "home_off_turnover_eligible_plays"
        ]
        if off_plays is None or off_plays < 150.0:
            raise ValueError(
                f"{result.season} offensive turnover-play sample depth "
                "is too low."
            )

        def_plays = result.sample_means[
            "home_def_turnover_eligible_plays_faced"
        ]
        if def_plays is None or def_plays < 150.0:
            raise ValueError(
                f"{result.season} defensive turnover-play sample depth "
                "is too low."
            )

        home_fumbles = result.sample_means["home_off_fumbles"]
        if home_fumbles is None or home_fumbles < 4.0:
            raise ValueError(
                f"{result.season} offensive fumble sample depth is too low."
            )

        def_fumbles = result.sample_means[
            "home_def_opponent_fumbles"
        ]
        if def_fumbles is None or def_fumbles < 4.0:
            raise ValueError(
                f"{result.season} defensive fumble sample depth is too low."
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


def format_report(
    results: list[SeasonValidation],
) -> str:
    lines = [
        "=" * 104,
        "PROJECT GRIDIRON — TURNOVER-STABILITY HISTORICAL VALIDATION",
        "=" * 104,
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
            lines.append(
                f"  {column:<48} {coverage:.1%}"
            )

        lines.append("Feature means / std:")
        for column in FEATURE_COLUMNS:
            mean = result.feature_mean[column]
            std = result.feature_std[column]
            lines.append(
                f"  {column:<48} "
                f"mean={mean: .4f}  std={std: .4f}"
            )

        lines.append("Sample depth means:")
        for column, value in result.sample_means.items():
            lines.append(
                f"  {column:<48} {value:.2f}"
            )

        lines.append("-" * 104)

    lines.append("STATUS: PASS")
    lines.append("=" * 104)
    return "\n".join(lines)


def main() -> int:
    results = validate_history(Path("."))
    print(format_report(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
