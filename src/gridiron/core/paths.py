"""Centralized filesystem paths for Project Gridiron."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    """Resolve canonical project paths from one repository root."""

    root: Path

    @classmethod
    def from_root(cls, root: Path | str = Path(".")) -> ProjectPaths:
        return cls(Path(root).resolve())

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def raw(self) -> Path:
        return self.data / "raw"

    @property
    def curated(self) -> Path:
        return self.data / "curated"

    @property
    def schedules(self) -> Path:
        return self.raw / "schedules"

    @property
    def play_by_play(self) -> Path:
        return self.raw / "play_by_play"

    @property
    def rest_features(self) -> Path:
        return self.curated / "rest_features"

    @property
    def qb_features(self) -> Path:
        return self.curated / "qb_features"

    @property
    def team_game_features(self) -> Path:
        return self.curated / "team_game_features"

    @property
    def team_ratings(self) -> Path:
        return self.curated / "team_ratings"

    @property
    def weekly_team_ratings(self) -> Path:
        return self.curated / "weekly_team_ratings"

    @property
    def strength_of_schedule(self) -> Path:
        return self.curated / "strength_of_schedule"

    @property
    def pgr(self) -> Path:
        return self.curated / "pgr"

    @property
    def predictions(self) -> Path:
        return self.curated / "predictions"

    @property
    def backtests(self) -> Path:
        return self.curated / "backtests"

    @property
    def reports(self) -> Path:
        return self.data / "reports"

    @property
    def backtest_reports(self) -> Path:
        return self.reports / "backtests"

    @property
    def database(self) -> Path:
        return self.root / "database"

    @property
    def metadata_database(self) -> Path:
        return self.database / "gridiron.duckdb"

    @property
    def output(self) -> Path:
        return self.root / "output"

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    def schedule_file(self, season: int) -> Path:
        _validate_season(season)
        return self.schedules / f"schedules_{season}.parquet"

    def play_by_play_file(self, season: int) -> Path:
        _validate_season(season)
        return (
            self.play_by_play
            / f"play_by_play_{season}.parquet"
        )

    def rest_features_file(self, season: int) -> Path:
        _validate_season(season)
        return (
            self.rest_features
            / f"rest_features_{season}.parquet"
        )

    def qb_features_file(self, season: int) -> Path:
        _validate_season(season)
        return self.qb_features / f"qb_features_{season}.parquet"

    def team_game_features_file(self, season: int) -> Path:
        _validate_season(season)
        return (
            self.team_game_features
            / f"team_game_features_{season}.parquet"
        )

    def team_ratings_file(self, season: int) -> Path:
        _validate_season(season)
        return self.team_ratings / f"team_ratings_{season}.parquet"

    def weekly_team_ratings_file(self, season: int) -> Path:
        _validate_season(season)
        return (
            self.weekly_team_ratings
            / f"weekly_team_ratings_{season}.parquet"
        )

    def strength_of_schedule_file(self, season: int) -> Path:
        _validate_season(season)
        return (
            self.strength_of_schedule
            / f"strength_of_schedule_{season}.parquet"
        )

    def pgr_file(self, season: int) -> Path:
        _validate_season(season)
        return self.pgr / f"pgr_{season}.parquet"

    def predictions_file(self, season: int) -> Path:
        _validate_season(season)
        return (
            self.predictions
            / f"predictions_{season}.parquet"
        )

    def backtest_file(self, season: int) -> Path:
        _validate_season(season)
        return self.backtests / f"backtest_{season}.parquet"

    def create_runtime_directories(self) -> None:
        """Create directories used by local pipelines."""
        for path in (
            self.schedules,
            self.play_by_play,
            self.rest_features,
            self.qb_features,
            self.team_game_features,
            self.team_ratings,
            self.weekly_team_ratings,
            self.strength_of_schedule,
            self.pgr,
            self.predictions,
            self.backtests,
            self.backtest_reports,
            self.database,
            self.output,
        ):
            path.mkdir(parents=True, exist_ok=True)


def _validate_season(season: int) -> None:
    if season < 1999 or season > 2100:
        raise ValueError(
            "NFL seasons must be between 1999 and 2100."
        )
