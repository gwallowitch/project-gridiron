"""Standalone turnover-regression feature pipeline."""

from __future__ import annotations

from pathlib import Path

from gridiron.data.nflverse import NFLVerseGateway
from gridiron.features.turnovers import build_turnover_features
from gridiron.validation.turnover_features import validate_turnover_features


def run_turnover_features_pipeline(
    season: int,
    *,
    project_root: Path | str = Path("."),
    gateway: NFLVerseGateway | None = None,
) -> Path:
    """Build and persist turnover features for one season."""
    root = Path(project_root).resolve()
    client = gateway or NFLVerseGateway()

    schedule = client.schedules([season])
    pbp = client.play_by_play([season])

    features = build_turnover_features(schedule, pbp)
    validate_turnover_features(features)

    output = (
        root
        / "data"
        / "curated"
        / "turnover_features"
        / f"turnover_features_{season}.parquet"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    temp = output.with_suffix(".tmp.parquet")
    features.write_parquet(temp)
    temp.replace(output)

    return output