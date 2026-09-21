"""Blinded, deterministic Step 92E historical spread request manifests."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from datetime import timedelta
from typing import Any

from gridiron.market.operational_history import canonical_json
from gridiron.market.operational_spreads import parse_timestamp

SCHEMA_VERSION = 1
PROVIDER = "the-odds-api"
SPORT_KEY = "americanfootball_nfl"
BOOKMAKER_KEYS = ("draftkings", "fanduel", "betmgm")
SAMPLE_SEASONS = (2021, 2023, 2025)
SAMPLE_REGULAR_WEEKS = (2, 8, 15)
TARGET_MINUTES = {
    "T12H": 720,
    "T6H": 360,
    "T3H": 180,
    "T1H": 60,
    "NEAR_KICKOFF": 15,
}
PROHIBITED_OUTCOME_FIELDS = frozenset(
    {
        "final_home_score", "final_away_score", "winner", "home_margin",
        "ats_margin", "cover_side", "profit", "roi",
    }
)


class HistoricalManifestError(ValueError):
    """The blinded historical acquisition manifest is invalid."""


def _digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _validate_game(raw: Mapping[str, Any]) -> dict[str, Any]:
    lowered = {str(key).lower() for key in raw}
    if lowered & PROHIBITED_OUTCOME_FIELDS:
        raise HistoricalManifestError("schedule must not contain outcome fields")
    required = {
        "game_id", "season", "season_type", "week", "home_team", "away_team",
        "kickoff_at",
    }
    if not required <= set(raw):
        raise HistoricalManifestError("schedule game is missing identity fields")
    season = raw["season"]
    week = raw["week"]
    if (
        isinstance(season, bool) or not isinstance(season, int)
        or isinstance(week, bool) or not isinstance(week, int)
        or not all(isinstance(raw[key], str) and raw[key] for key in required - {"season", "week"})
        or raw["home_team"] == raw["away_team"]
    ):
        raise HistoricalManifestError("invalid schedule game identity")
    kickoff = parse_timestamp(raw["kickoff_at"], "kickoff_at")
    return {
        "game_id": raw["game_id"], "season": season,
        "season_type": raw["season_type"], "week": week,
        "home_team": raw["home_team"], "away_team": raw["away_team"],
        "kickoff_at": kickoff.isoformat().replace("+00:00", "Z"),
    }


def select_blinded_sample(games: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Select fixed weeks and first games without reading outcome information."""
    validated = [_validate_game(game) for game in games]
    selected: list[dict[str, Any]] = []
    for season in SAMPLE_SEASONS:
        for week in SAMPLE_REGULAR_WEEKS:
            candidates = sorted(
                (
                    game for game in validated
                    if game["season"] == season
                    and game["season_type"] == "REG"
                    and game["week"] == week
                ),
                key=lambda game: (game["kickoff_at"], game["game_id"]),
            )
            selected.extend(candidates[:2])
        wild_cards = sorted(
            (
                game for game in validated
                if game["season"] == season
                and game["season_type"] in {"WC", "POST", "PST"}
                and game["week"] in {1, 19}
            ),
            key=lambda game: (game["kickoff_at"], game["game_id"]),
        )
        if wild_cards:
            selected.append(wild_cards[0])
    return tuple(selected)


def build_historical_manifest(
    games: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the frozen request plan without network or outcome data."""
    items: list[dict[str, Any]] = []
    for game in select_blinded_sample(games):
        kickoff = parse_timestamp(game["kickoff_at"], "kickoff_at")
        for label, minutes in TARGET_MINUTES.items():
            base = {
                "schema_version": SCHEMA_VERSION,
                "provider": PROVIDER,
                "sport_key": SPORT_KEY,
                "season": game["season"],
                "season_type": game["season_type"],
                "week": game["week"],
                "canonical_game_id": game["game_id"],
                "home_team": game["home_team"],
                "away_team": game["away_team"],
                "kickoff_at": game["kickoff_at"],
                "target_label": label,
                "target_minutes": minutes,
                "target_timestamp": (kickoff - timedelta(minutes=minutes)).isoformat().replace(
                    "+00:00", "Z"
                ),
                "market": "spreads",
                "region": "us",
                "bookmaker_keys": list(BOOKMAKER_KEYS),
                "odds_format": "american",
            }
            items.append({**base, "manifest_item_id": _digest(base)})
    items.sort(key=lambda item: (item["target_timestamp"], item["manifest_item_id"]))
    base_manifest = {
        "schema_version": SCHEMA_VERSION,
        "provider": PROVIDER,
        "sample_rule": "seasons-2021-2023-2025-reg-weeks-2-8-15-first-two-plus-first-wild-card-v1",
        "targets": dict(TARGET_MINUTES),
        "items": items,
    }
    return {**base_manifest, "manifest_sha256": _digest(base_manifest)}


def validate_historical_manifest(manifest: Mapping[str, Any]) -> None:
    """Fail closed if manifest content, item content, or identities changed."""
    required = {
        "schema_version", "provider", "sample_rule", "targets", "items",
        "manifest_sha256",
    }
    if set(manifest) != required or manifest.get("schema_version") != SCHEMA_VERSION:
        raise HistoricalManifestError("manifest schema is invalid")
    if manifest.get("provider") != PROVIDER or manifest.get("targets") != TARGET_MINUTES:
        raise HistoricalManifestError("manifest authority is invalid")
    items = manifest.get("items")
    if not isinstance(items, list):
        raise HistoricalManifestError("manifest items must be an array")
    identities: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            raise HistoricalManifestError("manifest item is invalid")
        material = dict(item)
        claimed = material.pop("manifest_item_id", None)
        if claimed != _digest(material) or claimed in identities:
            raise HistoricalManifestError("manifest item identity is invalid")
        identities.add(str(claimed))
    material = dict(manifest)
    claimed_manifest = material.pop("manifest_sha256")
    if claimed_manifest != _digest(material):
        raise HistoricalManifestError("manifest hash is invalid")


def estimate_cost(
    request_count: int,
    *,
    credits_per_request: int,
    plan_credit_allowance: int | None = None,
    plan_price: float | None = None,
) -> dict[str, Any]:
    """Pure estimate; all provider-plan assumptions are caller supplied."""
    if request_count < 0 or credits_per_request < 0:
        raise HistoricalManifestError("cost inputs must be nonnegative")
    total = request_count * credits_per_request
    return {
        "request_count": request_count,
        "credits_per_request": credits_per_request,
        "estimated_total_credits": total,
        "plan_credit_allowance": plan_credit_allowance,
        "allowance_covers_estimate": (
            None if plan_credit_allowance is None else plan_credit_allowance >= total
        ),
        "plan_price": plan_price,
    }


def manifest_json(manifest: Mapping[str, Any]) -> str:
    return canonical_json(manifest)


__all__ = [
    "BOOKMAKER_KEYS",
    "PROVIDER",
    "SAMPLE_REGULAR_WEEKS",
    "SAMPLE_SEASONS",
    "TARGET_MINUTES",
    "HistoricalManifestError",
    "build_historical_manifest",
    "estimate_cost",
    "manifest_json",
    "select_blinded_sample",
    "validate_historical_manifest",
]
