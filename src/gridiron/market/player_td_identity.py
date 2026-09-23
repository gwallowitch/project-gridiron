"""Fail-closed player identity results for ATTD evidence."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class ResolutionStatus(StrEnum):
    EXACT_PROVIDER_ID = "EXACT_PROVIDER_ID"
    EXACT_CROSSWALK = "EXACT_CROSSWALK"
    EXACT_NAME_TEAM = "EXACT_NAME_TEAM"
    EXACT_NAME_ROSTER = "EXACT_NAME_ROSTER"
    MANUAL_REVIEWED = "MANUAL_REVIEWED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    CONFLICT = "CONFLICT"


AUTHORITATIVE = frozenset(ResolutionStatus) - {
    ResolutionStatus.AMBIGUOUS, ResolutionStatus.UNRESOLVED, ResolutionStatus.CONFLICT,
}


def normalize_player_name(name: str) -> tuple[str, str | None]:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    parts = re.sub(r"[^a-zA-Z0-9 ]", " ", text).casefold().split()
    suffix = parts[-1] if parts and parts[-1] in {"jr", "sr", "ii", "iii", "iv"} else None
    if suffix:
        parts.pop()
    return " ".join(parts), suffix


@dataclass(frozen=True)
class PlayerResolution:
    raw_provider_player_name: str
    normalized_player_name: str
    suffix: str | None
    provider_event_id: str
    bookmaker: str
    player_team: str | None
    candidate_gsis_ids: tuple[str, ...]
    selected_gsis_id: str | None
    status: ResolutionStatus
    provenance: str
    manual_reviewer: str | None = None
    manual_reviewed_at: str | None = None

    @property
    def authoritative(self) -> bool:
        return self.status in AUTHORITATIVE and self.selected_gsis_id is not None

    def __post_init__(self) -> None:
        if self.status in {ResolutionStatus.AMBIGUOUS, ResolutionStatus.CONFLICT} and self.selected_gsis_id:
            raise ValueError("ambiguous or conflicting identity cannot select a GSIS ID")
        if self.status == ResolutionStatus.MANUAL_REVIEWED and not (
            self.manual_reviewer and self.manual_reviewed_at
        ):
            raise ValueError("manual resolution requires review provenance")


def resolve_exact_name_team(
    raw_name: str, team: str | None, roster: tuple[dict[str, str], ...], *,
    provider_event_id: str, bookmaker: str,
) -> PlayerResolution:
    normalized, suffix = normalize_player_name(raw_name)
    matches = [
        row for row in roster
        if normalize_player_name(row["name"])[0] == normalized
        and (team is None or row.get("team") == team)
    ]
    candidates = tuple(sorted({row["gsis_id"] for row in matches}))
    status = (
        ResolutionStatus.EXACT_NAME_TEAM if len(candidates) == 1 and team
        else ResolutionStatus.EXACT_NAME_ROSTER if len(candidates) == 1
        else ResolutionStatus.AMBIGUOUS if len(candidates) > 1
        else ResolutionStatus.UNRESOLVED
    )
    return PlayerResolution(
        raw_name, normalized, suffix, provider_event_id, bookmaker, team, candidates,
        candidates[0] if len(candidates) == 1 else None, status,
        "exact normalized name plus supplied roster/team only",
    )


__all__ = ["PlayerResolution", "ResolutionStatus", "normalize_player_name", "resolve_exact_name_team"]
