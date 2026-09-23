"""Outcome-free Step 93B future ATTD sample protocol."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import timedelta
from enum import StrEnum
from typing import Any

from gridiron.market.player_td_contract import MARKET_KEY, SPORT_KEY, parse_timestamp

SAMPLE_SCHEMA_VERSION = 1
SAMPLE_PROTOCOL_VERSION = "step93b-attd-schema-coverage-v1"
SAMPLE_SEASONS = (2023, 2024, 2025)
TARGETS = {"T12H": 720, "T1H": 60}
BOOKS = ("draftkings", "fanduel", "betmgm")
REGION = "us"
ODDS_FORMAT = "american"
MAX_REQUEST_COUNT = 6
ESTIMATED_CREDITS_PER_REQUEST = 10
PURPOSE = "SCHEMA_AND_COVERAGE_VALIDATION"
PROHIBITED_FIELD_TOKENS = (
    "score", "winner", "touchdown", "profit", "roi", "result", "injury",
)


class SampleReadiness(StrEnum):
    NOT_ACQUIRED = "ATTD_SAMPLE_NOT_ACQUIRED"
    ACQUIRED = "ATTD_SAMPLE_ACQUIRED"
    PARTIAL = "ATTD_SAMPLE_PARTIAL"
    SCHEMA_VALID = "ATTD_SAMPLE_SCHEMA_VALID"
    COVERAGE_INSUFFICIENT = "ATTD_SAMPLE_COVERAGE_INSUFFICIENT"
    IDENTITY_INSUFFICIENT = "ATTD_SAMPLE_IDENTITY_INSUFFICIENT"
    SETTLEMENT_UNRESOLVED = "ATTD_SAMPLE_SETTLEMENT_UNRESOLVED"
    FAILED = "ATTD_SAMPLE_FAILED"


class PlayerTDSampleError(ValueError):
    pass


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def build_sample_manifest(
    games: Sequence[Mapping[str, Any]], *,
    schedule_source_id: str = "synthetic-test-authority",
    schedule_artifact_sha256: str = "0" * 64,
) -> dict[str, Any]:
    validated: list[dict[str, Any]] = []
    for raw in games:
        lowered_fields = {str(key).casefold() for key in raw}
        if any(
            token in field
            for field in lowered_fields
            for token in PROHIBITED_FIELD_TOKENS
        ):
            raise PlayerTDSampleError("sample selection input contains prohibited outcome fields")
        required = {"game_id", "season", "season_type", "week", "home_team", "away_team", "kickoff_at"}
        if set(raw) != required or raw["season_type"] != "REG":
            raise PlayerTDSampleError("sample schedule identity is invalid")
        kickoff = parse_timestamp(raw["kickoff_at"], "kickoff_at")
        validated.append({**raw, "kickoff_at": kickoff.isoformat().replace("+00:00", "Z")})
    selected = []
    if not schedule_source_id or len(schedule_artifact_sha256) != 64:
        raise PlayerTDSampleError("schedule provenance is invalid")
    for season in SAMPLE_SEASONS:
        candidates = sorted(
            (row for row in validated if row["season"] == season),
            key=lambda row: (row["kickoff_at"], row["game_id"]),
        )
        if not candidates:
            raise PlayerTDSampleError(f"approved outcome-free schedule lacks season {season}")
        selected.append(candidates[0])
    items = []
    for game in selected:
        kickoff = parse_timestamp(game["kickoff_at"], "kickoff_at")
        for label, minutes in TARGETS.items():
            base = {
                "sample_schema_version": SAMPLE_SCHEMA_VERSION,
                "sample_protocol_version": SAMPLE_PROTOCOL_VERSION,
                "canonical_game_id": game["game_id"], "provider_event_id": None,
                "season": game["season"], "season_type": game["season_type"],
                "week": game["week"], "home_team": game["home_team"],
                "away_team": game["away_team"], "kickoff_at": game["kickoff_at"],
                "snapshot_label": label,
                "requested_snapshot_at": (
                    kickoff - timedelta(minutes=minutes)
                ).isoformat().replace("+00:00", "Z"),
                "sport": SPORT_KEY, "market": MARKET_KEY,
                "books": list(BOOKS), "region": REGION,
                "odds_format": ODDS_FORMAT, "purpose": PURPOSE,
                "schedule_source_id": schedule_source_id,
                "schedule_artifact_sha256": schedule_artifact_sha256,
            }
            items.append({**base, "sample_item_id": _digest(base)})
    items.sort(key=lambda item: (item["requested_snapshot_at"], item["sample_item_id"]))
    if len(items) > MAX_REQUEST_COUNT:
        raise PlayerTDSampleError("sample request ceiling exceeded")
    base = {
        "schema_version": SAMPLE_SCHEMA_VERSION,
        "protocol_version": SAMPLE_PROTOCOL_VERSION,
        "selection_rule": "first-REG-game-by-kickoff-then-canonical-game-id-per-2023-2024-2025",
        "targets": TARGETS, "maximum_request_count": MAX_REQUEST_COUNT,
        "estimated_credits_per_request": ESTIMATED_CREDITS_PER_REQUEST,
        "estimated_maximum_credits": MAX_REQUEST_COUNT * ESTIMATED_CREDITS_PER_REQUEST,
        "bulk_acquisition_authorized": False, "items": items,
    }
    return {**base, "manifest_sha256": _digest(base)}


def validate_sample_manifest(manifest: Mapping[str, Any]) -> None:
    """Fail closed if the frozen six-request manifest is altered."""
    required = {
        "schema_version", "protocol_version", "selection_rule", "targets",
        "maximum_request_count", "estimated_credits_per_request",
        "estimated_maximum_credits", "bulk_acquisition_authorized", "items",
        "manifest_sha256",
    }
    if set(manifest) != required:
        raise PlayerTDSampleError("sample manifest schema is invalid")
    items = manifest.get("items")
    if not isinstance(items, list) or len(items) != MAX_REQUEST_COUNT:
        raise PlayerTDSampleError("sample manifest must contain exactly six items")
    if manifest.get("bulk_acquisition_authorized") is not False:
        raise PlayerTDSampleError("sample manifest cannot authorize bulk acquisition")
    identities: set[str] = set()
    games_by_season: dict[int, set[str]] = {}
    snapshots_by_game: dict[str, set[str]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise PlayerTDSampleError("sample item is invalid")
        material = dict(item)
        claimed = material.pop("sample_item_id", None)
        if claimed != _digest(material) or claimed in identities:
            raise PlayerTDSampleError("sample item identity is invalid")
        identities.add(str(claimed))
        if (
            item.get("sample_schema_version") != SAMPLE_SCHEMA_VERSION
            or item.get("sample_protocol_version") != SAMPLE_PROTOCOL_VERSION
            or item.get("sport") != SPORT_KEY or item.get("market") != MARKET_KEY
            or tuple(item.get("books", ())) != BOOKS or item.get("region") != REGION
            or item.get("odds_format") != ODDS_FORMAT or item.get("purpose") != PURPOSE
            or item.get("season_type") != "REG"
            or item.get("snapshot_label") not in TARGETS
        ):
            raise PlayerTDSampleError("sample item frozen scope is invalid")
        season = item.get("season")
        game_id = item.get("canonical_game_id")
        if season not in SAMPLE_SEASONS or not isinstance(game_id, str):
            raise PlayerTDSampleError("sample item season or game is invalid")
        games_by_season.setdefault(season, set()).add(game_id)
        snapshots_by_game.setdefault(game_id, set()).add(str(item["snapshot_label"]))
    if set(games_by_season) != set(SAMPLE_SEASONS) or any(
        len(games) != 1 for games in games_by_season.values()
    ):
        raise PlayerTDSampleError("sample requires one game in each frozen season")
    if any(labels != set(TARGETS) for labels in snapshots_by_game.values()):
        raise PlayerTDSampleError("sample requires exact T12H and T1H snapshots")
    material = dict(manifest)
    claimed_manifest = material.pop("manifest_sha256")
    if claimed_manifest != _digest(material):
        raise PlayerTDSampleError("sample manifest SHA-256 is invalid")


def sample_manifest_json(manifest: Mapping[str, Any]) -> str:
    validate_sample_manifest(manifest)
    return _canonical(manifest)


__all__ = [
    "BOOKS",
    "MAX_REQUEST_COUNT",
    "PURPOSE",
    "PlayerTDSampleError",
    "SampleReadiness",
    "build_sample_manifest",
    "sample_manifest_json",
    "validate_sample_manifest",
]
