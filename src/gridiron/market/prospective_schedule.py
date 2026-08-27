"""Retain an NFLVerse schedule for Step 91I without mutating its source artifact."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import polars as pl

from gridiron.market.prospective_audit import canonical_json
from gridiron.market.prospective_integrity import canonical_game_id

SOURCE_TIMEZONE = ZoneInfo("America/New_York")
EXPECTED_SOURCE_SHA256 = (
    "c9c79a15b5c058890abe10a020753b0788d37f3cee4427316baa4a53fdb0335a"
)
EXPECTED_GAME_ID_DIGEST = (
    "8294140810d979df2a8d197b4d66361c15073a3904f6bb1a22a2031b09393fb2"
)
EXPECTED_RETAINED_SHA256 = (
    "d55f8ebff93bd2ad64702d2c2bb1391dc8770f60b9d6084770b3b8f5ca5a8803"
)
EXPECTED_WEEK_COUNTS = {
    1: 16,
    2: 16,
    3: 16,
    4: 16,
    5: 15,
    6: 14,
    7: 14,
    8: 14,
    9: 15,
    10: 14,
    11: 13,
    12: 16,
    13: 14,
    14: 15,
    15: 16,
    16: 16,
}
REQUIRED_SOURCE_COLUMNS = frozenset(
    {
        "game_id",
        "season",
        "game_type",
        "week",
        "gameday",
        "gametime",
        "away_team",
        "home_team",
    }
)
RETAINED_KEYS = frozenset(
    {
        "game_id",
        "season",
        "season_type",
        "week",
        "kickoff_at",
        "away_team",
        "home_team",
        "provider_ids",
    }
)


class ProspectiveScheduleError(ValueError):
    """Raised when schedule retention cannot preserve the Step 91I contract."""


def _source_kickoff(gameday: object, gametime: object) -> str:
    if not isinstance(gameday, str) or not isinstance(gametime, str):
        raise ProspectiveScheduleError("gameday and gametime must be strings")
    try:
        local = datetime.strptime(f"{gameday} {gametime}", "%Y-%m-%d %H:%M").replace(
            tzinfo=SOURCE_TIMEZONE
        )
    except ValueError as exc:
        raise ProspectiveScheduleError(
            f"malformed NFLVerse kickoff fields: {gameday} {gametime}"
        ) from exc
    return local.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _validate_week_counts(
    rows: Sequence[Mapping[str, Any]], expected: Mapping[int, int]
) -> None:
    actual = Counter(row["week"] for row in rows)
    if dict(sorted(actual.items())) != dict(sorted(expected.items())):
        raise ProspectiveScheduleError(
            f"incomplete 2026 REG Weeks 1-16 schedule: expected {dict(expected)}, "
            f"found {dict(sorted(actual.items()))}"
        )


def _game_id_digest(game_ids: set[str]) -> str:
    material = canonical_json(sorted(game_ids)).encode()
    return hashlib.sha256(material).hexdigest()


def build_retained_schedule(
    source: pl.DataFrame,
    *,
    expected_week_counts: Mapping[int, int] = EXPECTED_WEEK_COUNTS,
    expected_game_id_digest: str | None = EXPECTED_GAME_ID_DIGEST,
) -> list[dict[str, Any]]:
    """Convert the canonical NFLVerse frame into deterministic Step 91I rows."""
    missing_columns = sorted(REQUIRED_SOURCE_COLUMNS - set(source.columns))
    if missing_columns:
        raise ProspectiveScheduleError(
            f"canonical schedule is missing columns: {', '.join(missing_columns)}"
        )
    if source.height == 0:
        raise ProspectiveScheduleError("canonical schedule is empty")
    seasons = set(source["season"].to_list())
    if seasons != {2026}:
        raise ProspectiveScheduleError(
            f"canonical artifact must contain only season 2026; found {sorted(seasons)}"
        )

    target = source.filter(
        (pl.col("game_type") == "REG") & pl.col("week").is_between(1, 16)
    )
    rows: list[dict[str, Any]] = []
    canonical_ids: set[str] = set()
    provider_ids: set[str] = set()
    team_dates: set[tuple[str, str]] = set()
    for raw in target.iter_rows(named=True):
        week = raw["week"]
        if isinstance(week, bool) or not isinstance(week, int):
            raise ProspectiveScheduleError("week must be an integer")
        away = raw["away_team"]
        home = raw["home_team"]
        try:
            game_id = canonical_game_id(2026, week, away, home)
        except (TypeError, ValueError) as exc:
            raise ProspectiveScheduleError(
                f"invalid canonical game identity: {exc}"
            ) from exc
        if raw["game_id"] != game_id:
            raise ProspectiveScheduleError(
                f"NFLVerse game_id does not match canonical identity: {raw['game_id']}"
            )
        if game_id in canonical_ids:
            raise ProspectiveScheduleError(f"duplicate canonical ID: {game_id}")
        source_provider_id = raw["game_id"]
        if not isinstance(source_provider_id, str) or not source_provider_id:
            raise ProspectiveScheduleError("NFLVerse game_id provenance is unavailable")
        if source_provider_id in provider_ids:
            raise ProspectiveScheduleError(
                f"duplicate NFLVerse provider ID: {source_provider_id}"
            )
        for team in (away, home):
            team_date = (raw["gameday"], team)
            if team_date in team_dates:
                raise ProspectiveScheduleError(
                    f"duplicate team/date combination: {team} on {raw['gameday']}"
                )
            team_dates.add(team_date)
        canonical_ids.add(game_id)
        provider_ids.add(source_provider_id)
        rows.append(
            {
                "game_id": game_id,
                "season": 2026,
                "season_type": "REG",
                "week": week,
                "kickoff_at": _source_kickoff(raw["gameday"], raw["gametime"]),
                "away_team": away,
                "home_team": home,
                "provider_ids": [source_provider_id],
            }
        )
    rows.sort(key=lambda row: (row["week"], row["kickoff_at"], row["game_id"]))
    _validate_week_counts(rows, expected_week_counts)
    actual_digest = _game_id_digest(canonical_ids)
    if expected_game_id_digest is not None and actual_digest != expected_game_id_digest:
        raise ProspectiveScheduleError(
            "2026 game identity universe does not match the retained upstream contract; "
            f"expected {expected_game_id_digest}, found {actual_digest}"
        )
    validate_retained_schedule(
        rows,
        expected_game_ids=canonical_ids,
        expected_week_counts=expected_week_counts,
    )
    return rows


def validate_retained_schedule(
    rows: object,
    *,
    expected_game_ids: set[str],
    expected_week_counts: Mapping[int, int] = EXPECTED_WEEK_COUNTS,
) -> None:
    """Validate retained rows against the complete canonical-source denominator."""
    if not isinstance(rows, list):
        raise ProspectiveScheduleError("retained schedule must be a JSON list")
    canonical_ids: set[str] = set()
    provider_ids: set[str] = set()
    team_dates: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != RETAINED_KEYS:
            raise ProspectiveScheduleError(
                "retained schedule row has an invalid schema"
            )
        if row["season"] != 2026:
            raise ProspectiveScheduleError("retained schedule contains a non-2026 game")
        if row["season_type"] != "REG":
            raise ProspectiveScheduleError(
                "retained schedule contains a postseason game"
            )
        week = row["week"]
        if isinstance(week, bool) or not isinstance(week, int) or not 1 <= week <= 16:
            raise ProspectiveScheduleError(
                "retained schedule contains a week outside 1-16"
            )
        expected_id = canonical_game_id(2026, week, row["away_team"], row["home_team"])
        if row["game_id"] != expected_id:
            raise ProspectiveScheduleError("retained canonical game_id is malformed")
        if expected_id in canonical_ids:
            raise ProspectiveScheduleError(f"duplicate canonical ID: {expected_id}")
        canonical_ids.add(expected_id)
        providers = row["provider_ids"]
        if not isinstance(providers, list) or len(providers) != 1:
            raise ProspectiveScheduleError(
                "exactly one provenance-backed NFLVerse provider ID is required"
            )
        provider_id = providers[0]
        if provider_id in provider_ids:
            raise ProspectiveScheduleError(f"duplicate provider ID: {provider_id}")
        if provider_id != expected_id:
            raise ProspectiveScheduleError(
                "provider ID must be the exact retained NFLVerse game_id"
            )
        provider_ids.add(provider_id)
        try:
            kickoff = datetime.fromisoformat(row["kickoff_at"])
        except (AttributeError, ValueError) as exc:
            raise ProspectiveScheduleError("malformed kickoff_at timestamp") from exc
        if kickoff.tzinfo is None or kickoff.utcoffset() != UTC.utcoffset(kickoff):
            raise ProspectiveScheduleError("kickoff_at must be normalized to UTC")
        kickoff_date = kickoff.astimezone(SOURCE_TIMEZONE).date().isoformat()
        for team in (row["away_team"], row["home_team"]):
            team_date = (kickoff_date, team)
            if team_date in team_dates:
                raise ProspectiveScheduleError(
                    f"duplicate team/date combination: {team} on {kickoff_date}"
                )
            team_dates.add(team_date)
    _validate_week_counts(rows, expected_week_counts)
    missing = sorted(expected_game_ids - canonical_ids)
    extra = sorted(canonical_ids - expected_game_ids)
    if missing or extra:
        raise ProspectiveScheduleError(
            f"retained schedule denominator mismatch; missing={missing}, extra={extra}"
        )


def retain_schedule(
    source_path: Path | str,
    output_path: Path | str,
    *,
    expected_week_counts: Mapping[int, int] = EXPECTED_WEEK_COUNTS,
    enforce_published_contract: bool = True,
) -> dict[str, Any]:
    """Write once, or verify byte-identical, without changing the source parquet."""
    source_file = Path(source_path)
    output_file = Path(output_path)
    source_bytes = source_file.read_bytes()
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    if enforce_published_contract and source_digest != EXPECTED_SOURCE_SHA256:
        raise ProspectiveScheduleError(
            "upstream schedule SHA256 does not match the published retention contract"
        )
    rows = build_retained_schedule(
        pl.read_parquet(source_file),
        expected_week_counts=expected_week_counts,
        expected_game_id_digest=(
            EXPECTED_GAME_ID_DIGEST if enforce_published_contract else None
        ),
    )
    encoded = (canonical_json(rows) + "\n").encode()
    retained_digest = hashlib.sha256(encoded).hexdigest()
    if enforce_published_contract and retained_digest != EXPECTED_RETAINED_SHA256:
        raise ProspectiveScheduleError(
            "derived schedule SHA256 does not match the published retention contract"
        )
    if output_file.exists():
        if output_file.read_bytes() != encoded:
            raise ProspectiveScheduleError(
                "retained schedule already exists with different content"
            )
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(encoded)
    return {
        "source_path": str(source_file),
        "source_sha256": source_digest,
        "retained_path": str(output_file),
        "retained_sha256": retained_digest,
        "games": len(rows),
        "weeks": [1, 16],
        "complete": True,
        "source_timezone": "America/New_York",
        "output_timezone": "UTC",
        "provider_id_provenance": "exact NFLVerse game_id field",
    }


def validate_retained_file(
    source_path: Path | str,
    retained_path: Path | str,
    *,
    expected_week_counts: Mapping[int, int] = EXPECTED_WEEK_COUNTS,
    enforce_published_contract: bool = True,
) -> dict[str, Any]:
    """Read both artifacts and verify the retained denominator without writes."""
    source_file = Path(source_path)
    retained_file = Path(retained_path)
    source_bytes = source_file.read_bytes()
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    if enforce_published_contract and source_digest != EXPECTED_SOURCE_SHA256:
        raise ProspectiveScheduleError(
            "upstream schedule SHA256 does not match the published retention contract"
        )
    source = pl.read_parquet(source_file)
    expected = build_retained_schedule(
        source,
        expected_week_counts=expected_week_counts,
        expected_game_id_digest=(
            EXPECTED_GAME_ID_DIGEST if enforce_published_contract else None
        ),
    )
    try:
        retained_bytes = retained_file.read_bytes()
        retained = json.loads(retained_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProspectiveScheduleError(f"cannot read retained schedule: {exc}") from exc
    validate_retained_schedule(
        retained,
        expected_game_ids={row["game_id"] for row in expected},
        expected_week_counts=expected_week_counts,
    )
    expected_bytes = (canonical_json(expected) + "\n").encode()
    if retained != expected or retained_bytes != expected_bytes:
        raise ProspectiveScheduleError(
            "retained schedule bytes, ordering, or content are not canonical"
        )
    retained_digest = hashlib.sha256(retained_bytes).hexdigest()
    if enforce_published_contract and retained_digest != EXPECTED_RETAINED_SHA256:
        raise ProspectiveScheduleError(
            "retained schedule SHA256 does not match the published retention contract"
        )
    return {
        "games": len(retained),
        "complete": True,
        "source_sha256": source_digest,
        "retained_sha256": retained_digest,
        "game_id_digest": _game_id_digest({row["game_id"] for row in retained}),
    }


__all__ = [
    "EXPECTED_GAME_ID_DIGEST",
    "EXPECTED_RETAINED_SHA256",
    "EXPECTED_SOURCE_SHA256",
    "EXPECTED_WEEK_COUNTS",
    "ProspectiveScheduleError",
    "build_retained_schedule",
    "retain_schedule",
    "validate_retained_file",
    "validate_retained_schedule",
]
