"""Frozen, disabled authority for Step 93C historical event-ID resolution.

This module defines scope and deterministic future evidence destinations only.
It contains no provider transport, credential access, or execution activation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from gridiron.market.player_td_historical_authority import (
    FROZEN_MANIFEST_SHA256,
)

AUTHORITY_SCHEMA_VERSION = 1
AUTHORITY_VERSION = "step93j1a-historical-event-resolution-v1"
AUTHORITY_TYPE = "HISTORICAL_PLAYER_ATTD_EVENT_RESOLUTION_V1"
CLASSIFICATION = "HISTORICAL_NON_PRODUCTION_EVENT_ID_RESOLUTION"
PURPOSE = "RESOLVE_FROZEN_STEP93C_PROVIDER_EVENT_IDS"
SPORT = "americanfootball_nfl"
ENDPOINT_CLASS = "HISTORICAL_EVENTS"
ENDPOINT_PATH = "/v4/historical/sports/{sport}/events"
J1_AUTHORITY_SHA256 = (
    "4f7f3baab797051909c284f30102254e5d9f2f255e30ffb24c077bf984c2dd77"
)
MAXIMUM_DISCOVERY_REQUESTS = 3
DISCOVERY_CREDITS_PER_NONEMPTY_RESPONSE = 1
MARKET_REQUEST_COUNT = 6
MARKET_ESTIMATED_CREDITS = 60
MAXIMUM_ESTIMATED_COMBINED_CREDITS = 63
EVIDENCE_ROOT = Path(
    "data/research/player_td_validation/step93c_sample/event_resolution"
)
RESOLUTION_ARTIFACT = Path(
    "data/research/player_td_validation/step93c_sample/"
    "provider_event_resolution.json"
)

_TEAM_NAMES = {
    "BAL": "Baltimore Ravens",
    "DAL": "Dallas Cowboys",
    "DET": "Detroit Lions",
    "KC": "Kansas City Chiefs",
    "PHI": "Philadelphia Eagles",
}
_FROZEN_GAMES = (
    (
        "2023_01_DET_KC",
        "DET",
        "KC",
        "2023-09-08T00:20:00Z",
        "2023-09-07T12:20:00Z",
    ),
    (
        "2024_01_BAL_KC",
        "BAL",
        "KC",
        "2024-09-06T00:20:00Z",
        "2024-09-05T12:20:00Z",
    ),
    (
        "2025_01_DAL_PHI",
        "DAL",
        "PHI",
        "2025-09-05T00:20:00Z",
        "2025-09-04T12:20:00Z",
    ),
)

AUTHORITY_FIELDS = frozenset({
    "schema_version",
    "authority_version",
    "authority_type",
    "manifest_sha256",
    "j1_authority_sha256",
    "sport",
    "endpoint_class",
    "endpoint_path",
    "game_count",
    "maximum_discovery_request_count",
    "documented_credits_per_nonempty_discovery",
    "market_request_count",
    "market_estimated_credits",
    "maximum_estimated_combined_credits",
    "purpose",
    "classification",
    "evidence_root",
    "resolution_artifact",
    "games",
    "execution_enabled",
    "authority_sha256",
})


class EventResolutionAuthorityError(ValueError):
    """The Step 93J.1A authority or frozen inputs are invalid."""


class EventResolutionDestination(NamedTuple):
    response_path: Path
    metadata_path: Path


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _expected_games() -> list[dict[str, Any]]:
    return [
        {
            "canonical_game_id": game_id,
            "away_team": away,
            "home_team": home,
            "provider_away_team": _TEAM_NAMES[away],
            "provider_home_team": _TEAM_NAMES[home],
            "kickoff_at": kickoff,
            "discovery_date": discovery_date,
        }
        for game_id, away, home, kickoff, discovery_date in _FROZEN_GAMES
    ]


def _manifest_games(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("manifest_sha256") != FROZEN_MANIFEST_SHA256:
        raise EventResolutionAuthorityError("manifest is not the frozen Step 93C artifact")
    material = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if _digest(material) != FROZEN_MANIFEST_SHA256:
        raise EventResolutionAuthorityError("manifest content does not match its identity")
    items = manifest.get("items")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise EventResolutionAuthorityError("manifest items are invalid")
    by_game: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise EventResolutionAuthorityError("manifest item is invalid")
        game_id = item.get("canonical_game_id")
        if not isinstance(game_id, str):
            raise EventResolutionAuthorityError("manifest game identity is invalid")
        identity = {
            "canonical_game_id": game_id,
            "away_team": item.get("away_team"),
            "home_team": item.get("home_team"),
            "kickoff_at": item.get("kickoff_at"),
        }
        previous = by_game.setdefault(game_id, identity)
        if previous != identity:
            raise EventResolutionAuthorityError("manifest game identity is inconsistent")
    expected = _expected_games()
    expected_identity = [
        {key: game[key] for key in (
            "canonical_game_id", "away_team", "home_team", "kickoff_at"
        )}
        for game in expected
    ]
    if list(by_game.values()) != expected_identity:
        raise EventResolutionAuthorityError("manifest does not contain the frozen games")
    for game in expected:
        t12h = [
            item
            for item in items
            if item.get("canonical_game_id") == game["canonical_game_id"]
            and item.get("snapshot_label") == "T12H"
        ]
        if len(t12h) != 1 or t12h[0].get("requested_snapshot_at") != game["discovery_date"]:
            raise EventResolutionAuthorityError("frozen discovery date is invalid")
    return expected


def build_event_resolution_authority(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the deterministic, non-activating three-game discovery authority."""
    games = _manifest_games(manifest)
    base = {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "authority_version": AUTHORITY_VERSION,
        "authority_type": AUTHORITY_TYPE,
        "manifest_sha256": FROZEN_MANIFEST_SHA256,
        "j1_authority_sha256": J1_AUTHORITY_SHA256,
        "sport": SPORT,
        "endpoint_class": ENDPOINT_CLASS,
        "endpoint_path": ENDPOINT_PATH,
        "game_count": len(games),
        "maximum_discovery_request_count": MAXIMUM_DISCOVERY_REQUESTS,
        "documented_credits_per_nonempty_discovery": (
            DISCOVERY_CREDITS_PER_NONEMPTY_RESPONSE
        ),
        "market_request_count": MARKET_REQUEST_COUNT,
        "market_estimated_credits": MARKET_ESTIMATED_CREDITS,
        "maximum_estimated_combined_credits": MAXIMUM_ESTIMATED_COMBINED_CREDITS,
        "purpose": PURPOSE,
        "classification": CLASSIFICATION,
        "evidence_root": EVIDENCE_ROOT.as_posix(),
        "resolution_artifact": RESOLUTION_ARTIFACT.as_posix(),
        "games": games,
        "execution_enabled": False,
    }
    return {**base, "authority_sha256": _digest(base)}


def _expected_authority() -> dict[str, Any]:
    games = _expected_games()
    base = {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "authority_version": AUTHORITY_VERSION,
        "authority_type": AUTHORITY_TYPE,
        "manifest_sha256": FROZEN_MANIFEST_SHA256,
        "j1_authority_sha256": J1_AUTHORITY_SHA256,
        "sport": SPORT,
        "endpoint_class": ENDPOINT_CLASS,
        "endpoint_path": ENDPOINT_PATH,
        "game_count": len(games),
        "maximum_discovery_request_count": MAXIMUM_DISCOVERY_REQUESTS,
        "documented_credits_per_nonempty_discovery": (
            DISCOVERY_CREDITS_PER_NONEMPTY_RESPONSE
        ),
        "market_request_count": MARKET_REQUEST_COUNT,
        "market_estimated_credits": MARKET_ESTIMATED_CREDITS,
        "maximum_estimated_combined_credits": MAXIMUM_ESTIMATED_COMBINED_CREDITS,
        "purpose": PURPOSE,
        "classification": CLASSIFICATION,
        "evidence_root": EVIDENCE_ROOT.as_posix(),
        "resolution_artifact": RESOLUTION_ARTIFACT.as_posix(),
        "games": games,
        "execution_enabled": False,
    }
    return {**base, "authority_sha256": _digest(base)}


def validate_event_resolution_authority(artifact: Mapping[str, Any]) -> None:
    """Validate exact J.1A scope without permitting activation."""
    if set(artifact) != AUTHORITY_FIELDS:
        raise EventResolutionAuthorityError("event-resolution authority schema is invalid")
    expected = _expected_authority()
    if artifact != expected:
        raise EventResolutionAuthorityError("event-resolution authority scope is invalid")


def event_resolution_destination(
    artifact: Mapping[str, Any], canonical_game_id: str
) -> EventResolutionDestination:
    """Return deterministic future raw paths; perform no filesystem writes."""
    validate_event_resolution_authority(artifact)
    allowed = {game["canonical_game_id"] for game in artifact["games"]}
    if canonical_game_id not in allowed:
        raise EventResolutionAuthorityError("game is outside frozen resolution scope")
    stem = canonical_game_id.lower()
    return EventResolutionDestination(
        EVIDENCE_ROOT / f"{stem}.response.json",
        EVIDENCE_ROOT / f"{stem}.metadata.json",
    )


__all__ = [
    "AUTHORITY_TYPE",
    "EventResolutionAuthorityError",
    "EventResolutionDestination",
    "build_event_resolution_authority",
    "event_resolution_destination",
    "validate_event_resolution_authority",
]
