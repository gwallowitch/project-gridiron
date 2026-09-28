"""Offline-enforceable boundary for a future six-item ATTD acquisition."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from gridiron.market.player_td_sample import (
    MAX_REQUEST_COUNT,
    validate_frozen_sample_manifest,
)


class PlayerTDAcquisitionError(RuntimeError):
    """A frozen acquisition plan cannot proceed without expanding scope."""

    def __init__(self, message: str, *, attempted: int = 0) -> None:
        super().__init__(message)
        self.attempted = attempted


@dataclass(frozen=True)
class ResolvedSampleAuthorization:
    """One separately resolved provider event bound to one manifest item."""

    sample_item_id: str
    provider_event_id: str

    def __post_init__(self) -> None:
        if not self.sample_item_id or not self.provider_event_id:
            raise PlayerTDAcquisitionError(
                "all provider event identities must be resolved before acquisition"
            )


@dataclass(frozen=True)
class AuthorizedPlayerTDRequest:
    sample_item_id: str
    provider_event_id: str
    canonical_game_id: str
    requested_snapshot_at: str
    market: str
    books: tuple[str, ...]
    region: str
    odds_format: str


@dataclass(frozen=True)
class PlayerTDTransportResult:
    """Single response; expansion signals are always terminal."""

    succeeded: bool
    retry_required: bool = False
    pagination_required: bool = False
    fallback_required: bool = False


@dataclass(frozen=True)
class BoundedAcquisitionPlan:
    requests: tuple[AuthorizedPlayerTDRequest, ...]
    maximum_provider_interactions: int = MAX_REQUEST_COUNT


def build_bounded_acquisition_plan(
    manifest: Mapping[str, Any],
    schedule: object,
    provenance: Mapping[str, Any],
    authorizations: Sequence[ResolvedSampleAuthorization],
) -> BoundedAcquisitionPlan:
    """Create the exact six-call plan without discovery or provider access."""
    validate_frozen_sample_manifest(manifest, schedule, provenance)
    items = manifest["items"]
    if len(authorizations) != MAX_REQUEST_COUNT:
        raise PlayerTDAcquisitionError(
            "exactly six resolved authorizations are required before acquisition"
        )
    expected_ids = [item["sample_item_id"] for item in items]
    supplied_ids = [authorization.sample_item_id for authorization in authorizations]
    if supplied_ids != expected_ids or len(set(supplied_ids)) != MAX_REQUEST_COUNT:
        raise PlayerTDAcquisitionError(
            "authorizations must map one-to-one in frozen manifest order"
        )
    requests = tuple(
        AuthorizedPlayerTDRequest(
            sample_item_id=item["sample_item_id"],
            provider_event_id=authorization.provider_event_id,
            canonical_game_id=item["canonical_game_id"],
            requested_snapshot_at=item["requested_snapshot_at"],
            market=item["market"],
            books=tuple(item["books"]),
            region=item["region"],
            odds_format=item["odds_format"],
        )
        for item, authorization in zip(items, authorizations, strict=True)
    )
    return BoundedAcquisitionPlan(requests=requests)


def execute_bounded_acquisition(
    manifest: Mapping[str, Any],
    schedule: object,
    provenance: Mapping[str, Any],
    authorizations: Sequence[ResolvedSampleAuthorization],
    transport: Callable[[AuthorizedPlayerTDRequest], PlayerTDTransportResult],
) -> tuple[PlayerTDTransportResult, ...]:
    """Fail closed because no production Player ATTD transport is authorized."""
    del manifest, schedule, provenance, authorizations, transport
    raise PlayerTDAcquisitionError(
        "production Player ATTD transport is disabled; no activation mechanism exists"
    )


__all__ = [
    "AuthorizedPlayerTDRequest",
    "BoundedAcquisitionPlan",
    "PlayerTDAcquisitionError",
    "PlayerTDTransportResult",
    "ResolvedSampleAuthorization",
    "build_bounded_acquisition_plan",
    "execute_bounded_acquisition",
]
