"""Offline evidence contracts for player anytime-touchdown research."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from urllib.parse import parse_qsl, urlsplit

SCHEMA_VERSION = 1
SPORT_KEY = "americanfootball_nfl"
MARKET_KEY = "player_anytime_td"
BOOKMAKER_KEYS = {
    "draftkings": "DraftKings",
    "fanduel": "FanDuel",
    "betmgm": "BetMGM",
}


class PlayerTDContractError(ValueError):
    """Player-TD evidence is invalid or ambiguous."""


class PriceState(StrEnum):
    YES_AND_NO = "YES_AND_NO"
    YES_ONLY = "YES_ONLY"
    NO_ONLY = "NO_ONLY"
    NO_VALID_PRICE = "NO_VALID_PRICE"
    AMBIGUOUS_DUPLICATE = "AMBIGUOUS_DUPLICATE"
    UNSUPPORTED_STRUCTURE = "UNSUPPORTED_STRUCTURE"


class BoardStatus(StrEnum):
    COMPLETE_UNVERIFIED = "COMPLETE_UNVERIFIED"
    PARTIAL = "PARTIAL"
    EMPTY = "EMPTY"
    AMBIGUOUS = "AMBIGUOUS"
    MALFORMED = "MALFORMED"
    BOOK_MISSING = "BOOK_MISSING"
    MARKET_MISSING = "MARKET_MISSING"


class ParticipationState(StrEnum):
    INACTIVE = "INACTIVE"
    ACTIVE_NO_PLAY = "ACTIVE_NO_PLAY"
    PARTICIPATED = "PARTICIPATED"
    PARTICIPATION_UNKNOWN = "PARTICIPATION_UNKNOWN"


class TouchdownType(StrEnum):
    RUSHING = "RUSHING"
    RECEIVING = "RECEIVING"
    KICKOFF_RETURN = "KICKOFF_RETURN"
    PUNT_RETURN = "PUNT_RETURN"
    FUMBLE_RECOVERY_OFFENSE = "FUMBLE_RECOVERY_OFFENSE"
    FUMBLE_RECOVERY_DEFENSE = "FUMBLE_RECOVERY_DEFENSE"
    INTERCEPTION_RETURN = "INTERCEPTION_RETURN"
    OTHER_DEFENSIVE_RETURN = "OTHER_DEFENSIVE_RETURN"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class SettlementResult(StrEnum):
    WIN = "WIN"
    LOSS = "LOSS"
    VOID = "VOID"
    PUSH = "PUSH"
    UNRESOLVED = "UNRESOLVED"


class RuleAuthority(StrEnum):
    VERIFIED_CURRENT = "VERIFIED_CURRENT"
    VERIFIED_HISTORICAL = "VERIFIED_HISTORICAL"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class FeatureAuthority(StrEnum):
    POINT_IN_TIME_VERIFIED = "POINT_IN_TIME_VERIFIED"
    PREGAME_RECONSTRUCTABLE = "PREGAME_RECONSTRUCTABLE"
    LAGGED_POSTGAME_SOURCE = "LAGGED_POSTGAME_SOURCE"
    TIMING_UNKNOWN = "TIMING_UNKNOWN"
    PROHIBITED_FOR_TARGET_GAME = "PROHIBITED_FOR_TARGET_GAME"


class PersonnelAuthority(StrEnum):
    PREGAME_TIMESTAMP_VERIFIED = "PREGAME_TIMESTAMP_VERIFIED"
    PREGAME_RECONSTRUCTABLE = "PREGAME_RECONSTRUCTABLE"
    LAGGED_POSTGAME = "LAGGED_POSTGAME"
    TIMING_UNKNOWN = "TIMING_UNKNOWN"


def parse_timestamp(value: str, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise PlayerTDContractError(f"{field_name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PlayerTDContractError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise PlayerTDContractError(f"{field_name} must include a timezone")
    return parsed


def validate_american_price(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PlayerTDContractError("American price must be an integer")
    if -99 <= value <= 99:
        raise PlayerTDContractError("American price must be <= -100 or >= 100")
    return value


def raw_price_break_even(value: object) -> float:
    """Return RAW PRICE BREAK-EVEN, not fair or vig-free probability."""
    price = validate_american_price(value)
    return 100 / (price + 100) if price > 0 else abs(price) / (abs(price) + 100)


def normalize_bookmaker(provider_key: str) -> str | None:
    return BOOKMAKER_KEYS.get(provider_key)


@dataclass(frozen=True)
class PlayerPrice:
    raw_player_name: str
    yes_price: int | None = None
    no_price: int | None = None
    provider_player_id: str | None = None
    canonical_player_id: str | None = None
    player_team: str | None = None
    player_position: str | None = None
    duplicate_outcomes: bool = False

    def __post_init__(self) -> None:
        if not self.raw_player_name.strip():
            raise PlayerTDContractError("raw player name is required")
        if self.yes_price is not None:
            validate_american_price(self.yes_price)
        if self.no_price is not None:
            validate_american_price(self.no_price)

    @property
    def price_state(self) -> PriceState:
        if self.duplicate_outcomes:
            return PriceState.AMBIGUOUS_DUPLICATE
        if self.yes_price is not None and self.no_price is not None:
            return PriceState.YES_AND_NO
        if self.yes_price is not None:
            return PriceState.YES_ONLY
        if self.no_price is not None:
            return PriceState.NO_ONLY
        return PriceState.NO_VALID_PRICE


@dataclass(frozen=True)
class ATTDObservation:
    provider: str
    provider_event_id: str
    canonical_game_id: str
    season: int
    season_type: str
    week: int
    home_team: str
    away_team: str
    kickoff_at: str
    requested_snapshot_at: str
    provider_snapshot_at: str
    bookmaker_key: str
    bookmaker_last_update: str
    raw_artifact_sha256: str
    source_manifest_id: str
    acquisition_at: str
    players: tuple[PlayerPrice, ...]
    provider_market_key: str = MARKET_KEY
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise PlayerTDContractError("unsupported observation schema")
        if self.provider_market_key != MARKET_KEY:
            raise PlayerTDContractError("wrong or alternate touchdown market")
        if normalize_bookmaker(self.bookmaker_key) is None:
            raise PlayerTDContractError("unknown bookmaker cannot satisfy initial research books")
        if self.home_team == self.away_team:
            raise PlayerTDContractError("event teams must differ")
        if (
            isinstance(self.season, bool) or not isinstance(self.season, int)
            or isinstance(self.week, bool) or not isinstance(self.week, int)
            or self.canonical_game_id
            != f"{self.season}_{self.week:02d}_{self.away_team}_{self.home_team}"
        ):
            raise PlayerTDContractError("canonical event identity mismatch")
        kickoff = parse_timestamp(self.kickoff_at, "kickoff_at")
        requested = parse_timestamp(self.requested_snapshot_at, "requested_snapshot_at")
        provider = parse_timestamp(self.provider_snapshot_at, "provider_snapshot_at")
        updated = parse_timestamp(self.bookmaker_last_update, "bookmaker_last_update")
        parse_timestamp(self.acquisition_at, "acquisition_at")
        if not (provider <= requested < kickoff) or updated > provider:
            raise PlayerTDContractError("observation timestamps violate pregame ordering")
        if len(self.raw_artifact_sha256) != 64:
            raise PlayerTDContractError("raw artifact SHA-256 is invalid")
        lowered = [player.raw_player_name.casefold() for player in self.players]
        if len(lowered) != len(set(lowered)):
            raise PlayerTDContractError("duplicate player makes board ambiguous")

    @property
    def observation_id(self) -> str:
        material = (
            f"{self.provider}|{self.provider_event_id}|{self.canonical_game_id}|"
            f"{self.provider_snapshot_at}|{self.bookmaker_key}|{self.raw_artifact_sha256}"
        )
        return hashlib.sha256(material.encode()).hexdigest()


def board_diagnostic(
    players: tuple[PlayerPrice, ...], *, book_present: bool = True,
    market_present: bool = True, multiple_markets: bool = False,
) -> dict[str, Any]:
    names = [player.raw_player_name.casefold() for player in players]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if not book_present:
        status = BoardStatus.BOOK_MISSING
    elif not market_present:
        status = BoardStatus.MARKET_MISSING
    elif multiple_markets or duplicates or any(player.duplicate_outcomes for player in players):
        status = BoardStatus.AMBIGUOUS
    elif not players:
        status = BoardStatus.EMPTY
    else:
        status = BoardStatus.COMPLETE_UNVERIFIED
    return {
        "status": status.value,
        "structurally_valid": status == BoardStatus.COMPLETE_UNVERIFIED,
        "provider_board_completeness_verified": False,
        "player_count": len(players),
        "unique_player_count": len(set(names)),
        "yes_count": sum(player.yes_price is not None for player in players),
        "no_count": sum(player.no_price is not None for player in players),
        "both_count": sum(
            player.yes_price is not None and player.no_price is not None
            for player in players
        ),
        "duplicate_names": duplicates,
    }


def cross_book_diagnostic(boards: dict[str, tuple[PlayerPrice, ...]]) -> dict[str, Any]:
    sets = {key: {p.raw_player_name.casefold() for p in value} for key, value in boards.items()}
    union = set().union(*sets.values()) if sets else set()
    intersection = set.intersection(*sets.values()) if sets else set()
    return {
        "union": sorted(union), "intersection": sorted(intersection),
        "unique_by_book": {
            key: sorted(names - set().union(*(other for other_key, other in sets.items() if other_key != key)))
            for key, names in sets.items()
        },
    }


@dataclass(frozen=True)
class SettlementRule:
    sportsbook: str
    jurisdiction: str
    rule_version: str
    effective_from: str | None
    effective_to: str | None
    participation_requirement: str
    overtime_policy: str
    qualifying_td_types: frozenset[TouchdownType]
    inactive_policy: str
    dressed_no_snap_policy: str
    participated_no_td_policy: str
    abandoned_game_policy: str
    postponed_game_policy: str
    stat_correction_policy: str
    source_reference: str
    reviewed_at: str
    authority_status: RuleAuthority
    source_hash: str | None = None


@dataclass(frozen=True)
class FootballTDOutcome:
    source_dataset: str
    source_version: str
    source_artifact_sha256: str
    game_id: str
    player_gsis_id: str
    touchdown_type: TouchdownType
    play_id: str
    period: int
    overtime: bool
    source_observed_at: str
    correction_version: str
    correction_timestamp: str | None = None
    predecessor_artifact_sha256: str | None = None


def settle_attd(
    *, rule: SettlementRule | None, player_resolved: bool, event_resolved: bool,
    participation: ParticipationState, touchdowns: tuple[FootballTDOutcome, ...],
) -> SettlementResult:
    if (
        rule is None or rule.authority_status == RuleAuthority.UNKNOWN
        or not player_resolved or not event_resolved
        or participation == ParticipationState.PARTICIPATION_UNKNOWN
    ):
        return SettlementResult.UNRESOLVED
    if participation in {ParticipationState.INACTIVE, ParticipationState.ACTIVE_NO_PLAY}:
        return SettlementResult.VOID if "VOID" in rule.inactive_policy.upper() else SettlementResult.UNRESOLVED
    if any(td.touchdown_type in rule.qualifying_td_types for td in touchdowns):
        return SettlementResult.WIN
    return SettlementResult.LOSS


@dataclass(frozen=True)
class FeatureEvidence:
    name: str
    observed_at: str
    prediction_cutoff_at: str
    kickoff_at: str
    authority: FeatureAuthority
    target_game_realized: bool = False

    def validate_for_prediction(self) -> None:
        observed = parse_timestamp(self.observed_at, "observed_at")
        cutoff = parse_timestamp(self.prediction_cutoff_at, "prediction_cutoff_at")
        kickoff = parse_timestamp(self.kickoff_at, "kickoff_at")
        if self.target_game_realized or self.authority in {
            FeatureAuthority.TIMING_UNKNOWN,
            FeatureAuthority.PROHIBITED_FOR_TARGET_GAME,
        }:
            raise PlayerTDContractError("feature is not verified for pregame use")
        if not observed <= cutoff < kickoff:
            raise PlayerTDContractError("feature violates prediction cutoff")


@dataclass(frozen=True)
class PersonnelEvidence:
    player_id: str
    team: str
    source: str
    source_artifact: str
    source_version: str
    observed_at: str | None
    effective_date: str | None
    authority: PersonnelAuthority
    source_hash: str
    injury_type: str | None = None
    practice_status: str | None = None
    game_status: str | None = None
    roster_status: str | None = None
    depth_position: str | None = None
    depth_rank: int | None = None
    active_status: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


def build_raw_artifact_metadata(
    raw: bytes, *, provider: str, sample_item_id: str,
    provider_event_id: str | None, requested_snapshot: str,
    returned_provider_snapshot: str | None, acquired_at: str, http_status: int,
    request_market: str, requested_books: tuple[str, ...], region: str,
    odds_format: str, request_url: str | None = None,
) -> dict[str, Any]:
    if request_market != MARKET_KEY:
        raise PlayerTDContractError("raw artifact market must be player_anytime_td")
    if request_url is not None:
        query_keys = {key.casefold() for key, _ in parse_qsl(urlsplit(request_url).query)}
        if query_keys & {"api_key", "apikey", "key", "token", "authorization"}:
            raise PlayerTDContractError("secret-bearing URL is prohibited")
    return {
        "schema_version": SCHEMA_VERSION, "provider": provider,
        "sample_item_id": sample_item_id, "provider_event_id": provider_event_id,
        "requested_snapshot": requested_snapshot,
        "returned_provider_snapshot": returned_provider_snapshot,
        "acquired_at": acquired_at, "http_status": http_status,
        "raw_byte_count": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "request_market": request_market, "requested_books": list(requested_books),
        "region": region, "odds_format": odds_format,
    }


__all__ = [name for name in globals() if not name.startswith("_")]
