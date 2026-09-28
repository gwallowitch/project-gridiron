"""Pinned, outcome-free schedule authority for Step 93C."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import polars as pl

from gridiron.market.player_td_sample import (
    SAMPLE_SEASONS,
    build_sample_manifest,
    sample_manifest_json,
    validate_frozen_sample_manifest,
)

SOURCE_TIMEZONE = ZoneInfo("America/New_York")
SOURCE_ID = "nflverse-schedules-release-games-parquet-asset-584596352"
SOURCE_RELEASE_URL = "https://github.com/nflverse/nflverse-data/releases/tag/schedules"
SOURCE_ASSET_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet"
)
SOURCE_RELEASE_ID = 251386473
SOURCE_ASSET_ID = 584596352
SOURCE_TAG_COMMIT = "ab1331c85fd222ce953fe61363b099c0629de0a1"
SOURCE_SHA256 = "edde2cff36388e86dfe0f1087cf9d1735c2d95f46079f55fbc7825956b877530"
SOURCE_SIZE = 521022
SOURCE_ASSET_CREATED_AT = "2026-09-23T21:16:18Z"
SOURCE_ASSET_UPDATED_AT = "2026-09-23T21:16:18Z"
TRANSFORM_VERSION = "step93c-outcome-free-attd-schedule-v1"
ALLOWED_FIELDS = (
    "game_id", "season", "season_type", "week", "home_team", "away_team",
    "kickoff_at",
)
SOURCE_FIELDS = {
    "game_id", "season", "game_type", "week", "gameday", "gametime",
    "home_team", "away_team",
}
PROHIBITED_FIELD_TOKENS = (
    "score", "winner", "margin", "spread", "moneyline", "total", "touchdown",
    "player", "injury", "profit", "roi", "result",
)


class PlayerTDScheduleError(ValueError):
    """Step 93C schedule authority or artifact is invalid."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _kickoff(gameday: object, gametime: object) -> str:
    if not isinstance(gameday, str) or not isinstance(gametime, str):
        raise PlayerTDScheduleError("source kickoff fields must be strings")
    try:
        local = datetime.strptime(f"{gameday} {gametime}", "%Y-%m-%d %H:%M").replace(
            tzinfo=SOURCE_TIMEZONE
        )
    except ValueError as exc:
        raise PlayerTDScheduleError("source kickoff fields are malformed") from exc
    return local.astimezone(UTC).isoformat().replace("+00:00", "Z")


def transform_outcome_free_schedule(source: pl.DataFrame) -> list[dict[str, Any]]:
    """Project only schedule identity before any sample selection."""
    missing = SOURCE_FIELDS - set(source.columns)
    if missing:
        raise PlayerTDScheduleError("source schedule is missing required identity fields")
    projected = source.filter(
        pl.col("season").is_in(SAMPLE_SEASONS) & (pl.col("game_type") == "REG")
    ).select(sorted(SOURCE_FIELDS))
    rows: list[dict[str, Any]] = []
    identities: set[str] = set()
    for raw in projected.iter_rows(named=True):
        season, week = raw["season"], raw["week"]
        if (
            isinstance(season, bool) or not isinstance(season, int)
            or isinstance(week, bool) or not isinstance(week, int)
        ):
            raise PlayerTDScheduleError("season and week must be integers")
        expected_id = f"{season}_{week:02d}_{raw['away_team']}_{raw['home_team']}"
        if raw["game_id"] != expected_id or expected_id in identities:
            raise PlayerTDScheduleError("canonical game identity is invalid")
        identities.add(expected_id)
        row = {
            "game_id": expected_id, "season": season, "season_type": "REG",
            "week": week, "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "kickoff_at": _kickoff(raw["gameday"], raw["gametime"]),
        }
        if tuple(row) != ALLOWED_FIELDS:
            raise PlayerTDScheduleError("derived schedule allowlist changed")
        if any(
            token in field.casefold()
            for field in row
            for token in PROHIBITED_FIELD_TOKENS
        ):
            raise PlayerTDScheduleError("derived schedule contains a prohibited field")
        rows.append(row)
    rows.sort(key=lambda row: (row["season"], row["kickoff_at"], row["game_id"]))
    counts = {season: sum(row["season"] == season for row in rows) for season in SAMPLE_SEASONS}
    if any(count != 272 for count in counts.values()):
        raise PlayerTDScheduleError("eligible schedule must contain 272 REG games per season")
    return rows


def validate_derived_schedule(rows: object) -> None:
    if not isinstance(rows, list):
        raise PlayerTDScheduleError("derived schedule must be an array")
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != set(ALLOWED_FIELDS):
            raise PlayerTDScheduleError("derived schedule violates the field allowlist")
        if any(
            token in str(field).casefold()
            for field in row
            for token in PROHIBITED_FIELD_TOKENS
        ):
            raise PlayerTDScheduleError("derived schedule contains a prohibited field")
    if len(rows) != 816:
        raise PlayerTDScheduleError("derived schedule must contain exactly 816 games")
    identities: set[str] = set()
    counts = {season: 0 for season in SAMPLE_SEASONS}
    previous: tuple[int, str, str] | None = None
    for row in rows:
        season = row["season"]
        week = row["week"]
        if (
            isinstance(season, bool)
            or not isinstance(season, int)
            or season not in SAMPLE_SEASONS
            or isinstance(week, bool)
            or not isinstance(week, int)
            or row["season_type"] != "REG"
        ):
            raise PlayerTDScheduleError("derived schedule population is invalid")
        expected_id = f"{season}_{week:02d}_{row['away_team']}_{row['home_team']}"
        if row["game_id"] != expected_id or expected_id in identities:
            raise PlayerTDScheduleError("derived schedule game identity is invalid")
        identities.add(expected_id)
        kickoff = row["kickoff_at"]
        if not isinstance(kickoff, str):
            raise PlayerTDScheduleError("derived schedule kickoff is invalid")
        try:
            parsed = datetime.fromisoformat(kickoff)
        except ValueError as exc:
            raise PlayerTDScheduleError("derived schedule kickoff is invalid") from exc
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise PlayerTDScheduleError("derived schedule kickoff must be UTC")
        identity = (season, kickoff, expected_id)
        if previous is not None and identity <= previous:
            raise PlayerTDScheduleError("derived schedule ordering is invalid")
        previous = identity
        counts[season] += 1
    if any(count != 272 for count in counts.values()):
        raise PlayerTDScheduleError("derived schedule must contain 272 games per season")


def materialize_schedule_and_manifest(
    source_path: Path | str, output_root: Path | str, *, retrieved_at: datetime,
) -> dict[str, Any]:
    """Verify the pinned raw asset, derive safe artifacts, and retain no raw bytes."""
    raw = Path(source_path).read_bytes()
    if len(raw) != SOURCE_SIZE or _sha(raw) != SOURCE_SHA256:
        raise PlayerTDScheduleError("raw source identity does not match the pinned asset")
    schedule = transform_outcome_free_schedule(pl.read_parquet(raw))
    validate_derived_schedule(schedule)
    schedule_bytes = (_canonical(schedule) + "\n").encode()
    schedule_sha = _sha(schedule_bytes)
    manifest = build_sample_manifest(
        schedule, schedule_source_id=SOURCE_ID,
        schedule_artifact_sha256=schedule_sha,
    )
    provenance = {
        "schema_version": 1, "source_provider": "nflverse/nflverse-data",
        "source_release_url": SOURCE_RELEASE_URL, "source_asset_url": SOURCE_ASSET_URL,
        "source_release_id": SOURCE_RELEASE_ID, "source_asset_id": SOURCE_ASSET_ID,
        "source_tag_commit": SOURCE_TAG_COMMIT, "source_sha256": SOURCE_SHA256,
        "source_asset_size": SOURCE_SIZE,
        "source_asset_created_at": SOURCE_ASSET_CREATED_AT,
        "source_asset_updated_at": SOURCE_ASSET_UPDATED_AT,
        "retrieved_at": retrieved_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "transform_version": TRANSFORM_VERSION, "allowed_fields": list(ALLOWED_FIELDS),
        "derived_schedule_sha256": schedule_sha, "raw_retained": False,
        "raw_retention_reason": "outcome-bearing upstream verified then deleted",
    }
    validate_frozen_sample_manifest(manifest, schedule, provenance)
    manifest_bytes = (sample_manifest_json(manifest) + "\n").encode()
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "player_td_schedule_2023_2025_v1.json": schedule_bytes,
        "player_td_schedule_2023_2025_v1.sha256": (schedule_sha + "\n").encode(),
        "schedule_provenance.json": (_canonical(provenance) + "\n").encode(),
        "step93c_player_td_sample_manifest.json": manifest_bytes,
        "step93c_player_td_sample_manifest.sha256": (
            manifest["manifest_sha256"] + "\n"
        ).encode(),
    }
    for name, content in artifacts.items():
        path = root / name
        if path.exists() and path.read_bytes() != content:
            raise PlayerTDScheduleError(f"immutable artifact conflict: {name}")
        if not path.exists():
            path.write_bytes(content)
    return {
        "schedule_rows": len(schedule), "schedule_sha256": schedule_sha,
        "manifest_sha256": manifest["manifest_sha256"],
        "request_count": len(manifest["items"]),
    }


__all__ = [
    "ALLOWED_FIELDS",
    "SOURCE_ASSET_ID",
    "SOURCE_SHA256",
    "PlayerTDScheduleError",
    "materialize_schedule_and_manifest",
    "transform_outcome_free_schedule",
    "validate_derived_schedule",
]
