"""Pinned, outcome-free schedule authority for Step 92F."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import polars as pl

from gridiron.market.historical_spread_manifest import (
    SAMPLE_REGULAR_WEEKS,
    SAMPLE_SEASONS,
    build_historical_manifest,
    validate_historical_manifest,
)
from gridiron.market.operational_history import canonical_json

SOURCE_TIMEZONE = ZoneInfo("America/New_York")
TRANSFORM_VERSION = "step92f-outcome-free-schedule-v1"
SOURCE_RELEASE_URL = "https://github.com/nflverse/nflverse-data/releases/tag/schedules"
SOURCE_ASSET_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet"
)
SOURCE_RELEASE_ID = 251386473
SOURCE_ASSET_ID = 579741037
SOURCE_TAG_COMMIT = "ab1331c85fd222ce953fe61363b099c0629de0a1"
SOURCE_SHA256 = "660fd3ee7cf75417358bae421c0471459a43005cbff015129ec1da625bf12fb4"
ALLOWED_FIELDS = (
    "game_id", "season", "season_type", "week", "home_team", "away_team",
    "kickoff_at",
)
SOURCE_FIELDS = {
    "game_id", "season", "game_type", "week", "gameday", "gametime",
    "home_team", "away_team",
}


class HistoricalScheduleError(ValueError):
    """Historical schedule provenance or identity is invalid."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _kickoff(gameday: object, gametime: object) -> str:
    if not isinstance(gameday, str) or not isinstance(gametime, str):
        raise HistoricalScheduleError("source kickoff fields must be strings")
    try:
        local = datetime.strptime(f"{gameday} {gametime}", "%Y-%m-%d %H:%M").replace(
            tzinfo=SOURCE_TIMEZONE
        )
    except ValueError as exc:
        raise HistoricalScheduleError("source kickoff fields are malformed") from exc
    return local.astimezone(UTC).isoformat().replace("+00:00", "Z")


def transform_outcome_free_schedule(source: pl.DataFrame) -> list[dict[str, Any]]:
    """Allowlist schedule identity; never project scores, lines, or outcomes."""
    missing = SOURCE_FIELDS - set(source.columns)
    if missing:
        raise HistoricalScheduleError(
            "source schedule is missing fields: " + ", ".join(sorted(missing))
        )
    filtered = source.filter(
        pl.col("season").is_in(SAMPLE_SEASONS)
        & (
            (
                (pl.col("game_type") == "REG")
                & pl.col("week").is_in(SAMPLE_REGULAR_WEEKS)
            )
            | (pl.col("game_type") == "WC")
        )
    ).select(sorted(SOURCE_FIELDS))
    rows: list[dict[str, Any]] = []
    identities: set[str] = set()
    for raw in filtered.iter_rows(named=True):
        season, week = raw["season"], raw["week"]
        if (
            isinstance(season, bool) or not isinstance(season, int)
            or isinstance(week, bool) or not isinstance(week, int)
            or raw["game_type"] not in {"REG", "WC"}
        ):
            raise HistoricalScheduleError("invalid season, type, or week")
        if not all(
            isinstance(raw[field], str) and raw[field]
            for field in ("away_team", "home_team")
        ):
            raise HistoricalScheduleError("source team identity is invalid")
        expected_id = (
            f"{season}_{week:02d}_{raw['away_team']}_{raw['home_team']}"
        )
        if raw["game_id"] != expected_id or expected_id in identities:
            raise HistoricalScheduleError("source canonical game identity is invalid")
        identities.add(expected_id)
        row = {
            "game_id": expected_id,
            "season": season,
            "season_type": raw["game_type"],
            "week": week,
            "home_team": raw["home_team"],
            "away_team": raw["away_team"],
            "kickoff_at": _kickoff(raw["gameday"], raw["gametime"]),
        }
        if tuple(row) != ALLOWED_FIELDS:
            raise HistoricalScheduleError("derived schedule allowlist changed")
        rows.append(row)
    rows.sort(key=lambda row: (row["season"], row["season_type"], row["week"], row["kickoff_at"], row["game_id"]))
    expected_groups = {
        (season, season_type, week)
        for season in SAMPLE_SEASONS
        for season_type, week in (
            *(("REG", week) for week in SAMPLE_REGULAR_WEEKS),
            ("WC", 19),
        )
    }
    actual_groups = {(row["season"], row["season_type"], row["week"]) for row in rows}
    if actual_groups != expected_groups:
        raise HistoricalScheduleError("derived schedule does not cover the frozen sample")
    return rows


def validate_schedule_provenance(provenance: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "source_provider", "source_release_url", "source_asset_url",
        "source_release_id", "source_asset_id", "source_tag_commit", "source_sha256",
        "source_asset_size", "source_asset_created_at", "source_asset_updated_at",
        "retrieved_at", "transform_version", "raw_retained", "raw_retention_reason",
        "derived_schedule_sha256",
    }
    if set(provenance) != required:
        raise HistoricalScheduleError("schedule provenance schema is invalid")
    expected = {
        "schema_version": 1,
        "source_provider": "nflverse/nflverse-data",
        "source_release_url": SOURCE_RELEASE_URL,
        "source_asset_url": SOURCE_ASSET_URL,
        "source_release_id": SOURCE_RELEASE_ID,
        "source_asset_id": SOURCE_ASSET_ID,
        "source_tag_commit": SOURCE_TAG_COMMIT,
        "source_sha256": SOURCE_SHA256,
        "source_asset_size": 520852,
        "source_asset_created_at": "2026-09-21T19:46:24Z",
        "source_asset_updated_at": "2026-09-21T19:46:25Z",
        "transform_version": TRANSFORM_VERSION,
        "raw_retained": False,
        "raw_retention_reason": "outcome-bearing upstream omitted; immutable locator and SHA-256 retained",
    }
    for field, value in expected.items():
        if provenance.get(field) != value:
            raise HistoricalScheduleError(f"schedule provenance {field} is invalid")
    try:
        retrieved = datetime.fromisoformat(str(provenance["retrieved_at"]))
    except ValueError as exc:
        raise HistoricalScheduleError("retrieval timestamp is invalid") from exc
    if retrieved.tzinfo is None:
        raise HistoricalScheduleError("retrieval timestamp must include a timezone")
    if not isinstance(provenance["derived_schedule_sha256"], str) or len(provenance["derived_schedule_sha256"]) != 64:
        raise HistoricalScheduleError("derived schedule SHA-256 is invalid")


def build_review_report(schedule: list[dict[str, Any]], manifest: Mapping[str, Any]) -> str:
    selected_ids = {item["canonical_game_id"] for item in manifest["items"]}
    selected = [row for row in schedule if row["game_id"] in selected_ids]
    lines = [
        "# Step 92F blinded historical acquisition manifest review",
        "", "Outcome-free schedule identity only. No odds were acquired.", "",
    ]
    by_game: dict[str, list[Mapping[str, Any]]] = {}
    for item in manifest["items"]:
        by_game.setdefault(str(item["canonical_game_id"]), []).append(item)
    for game in sorted(selected, key=lambda row: (row["kickoff_at"], row["game_id"])):
        lines.extend(
            (
                f"## {game['season']} {game['season_type']} {game['week']} — {game['away_team']} @ {game['home_team']}",
                "",
                f"- Canonical game ID: `{game['game_id']}`",
                f"- Kickoff UTC: `{game['kickoff_at']}`",
            )
        )
        for item in sorted(by_game[game["game_id"]], key=lambda value: value["target_minutes"], reverse=True):
            lines.append(f"- {item['target_label']}: `{item['target_timestamp']}`")
        lines.append("")
    return "\n".join(lines)


def materialize_schedule_and_manifest(
    source_path: Path | str,
    output_root: Path | str,
    *,
    retrieved_at: datetime,
) -> dict[str, Any]:
    """Verify the pinned raw asset and write deterministic reference artifacts."""
    source_file = Path(source_path)
    raw = source_file.read_bytes()
    if _sha(raw) != SOURCE_SHA256:
        raise HistoricalScheduleError("raw source SHA-256 does not match pinned asset")
    schedule = transform_outcome_free_schedule(pl.read_parquet(raw))
    schedule_bytes = (canonical_json(schedule) + "\n").encode()
    schedule_sha = _sha(schedule_bytes)
    manifest = build_historical_manifest(schedule)
    validate_historical_manifest(manifest)
    manifest_bytes = (canonical_json(manifest) + "\n").encode()
    provenance = {
        "schema_version": 1,
        "source_provider": "nflverse/nflverse-data",
        "source_release_url": SOURCE_RELEASE_URL,
        "source_asset_url": SOURCE_ASSET_URL,
        "source_release_id": SOURCE_RELEASE_ID,
        "source_asset_id": SOURCE_ASSET_ID,
        "source_tag_commit": SOURCE_TAG_COMMIT,
        "source_sha256": SOURCE_SHA256,
        "source_asset_size": len(raw),
        "source_asset_created_at": "2026-09-21T19:46:24Z",
        "source_asset_updated_at": "2026-09-21T19:46:25Z",
        "retrieved_at": retrieved_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "transform_version": TRANSFORM_VERSION,
        "raw_retained": False,
        "raw_retention_reason": "outcome-bearing upstream omitted; immutable locator and SHA-256 retained",
        "derived_schedule_sha256": schedule_sha,
    }
    validate_schedule_provenance(provenance)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "historical_spread_schedule_v1.json": schedule_bytes,
        "historical_spread_schedule_v1.sha256": (schedule_sha + "\n").encode(),
        "step92f_manifest.json": manifest_bytes,
        "step92f_manifest.sha256": (manifest["manifest_sha256"] + "\n").encode(),
        "schedule_provenance.json": (canonical_json(provenance) + "\n").encode(),
        "step92f_manifest_review.md": build_review_report(schedule, manifest).encode(),
    }
    for name, content in artifacts.items():
        path = root / name
        if path.exists() and path.read_bytes() != content:
            raise HistoricalScheduleError(f"immutable artifact conflict: {name}")
        if not path.exists():
            path.write_bytes(content)
    return {
        "schedule_rows": len(schedule),
        "schedule_sha256": schedule_sha,
        "manifest_sha256": manifest["manifest_sha256"],
        "request_count": len(manifest["items"]),
    }


__all__ = [
    "ALLOWED_FIELDS",
    "SOURCE_ASSET_ID",
    "SOURCE_SHA256",
    "TRANSFORM_VERSION",
    "HistoricalScheduleError",
    "build_review_report",
    "materialize_schedule_and_manifest",
    "transform_outcome_free_schedule",
    "validate_schedule_provenance",
]
