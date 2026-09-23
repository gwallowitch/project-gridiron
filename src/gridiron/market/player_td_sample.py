"""Outcome-free Step 93B future ATTD sample protocol."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import timedelta
from enum import StrEnum
from typing import Any

from gridiron.market.player_td_contract import MARKET_KEY, parse_timestamp

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


def build_sample_manifest(games: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
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
                "target_label": label,
                "requested_historical_snapshot": (
                    kickoff - timedelta(minutes=minutes)
                ).isoformat().replace("+00:00", "Z"),
                "market": MARKET_KEY, "books": list(BOOKS), "region": REGION,
                "odds_format": ODDS_FORMAT, "purpose": PURPOSE,
            }
            items.append({**base, "sample_item_id": _digest(base)})
    items.sort(key=lambda item: (item["requested_historical_snapshot"], item["sample_item_id"]))
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


__all__ = [
    "BOOKS",
    "MAX_REQUEST_COUNT",
    "PURPOSE",
    "PlayerTDSampleError",
    "SampleReadiness",
    "build_sample_manifest",
]
