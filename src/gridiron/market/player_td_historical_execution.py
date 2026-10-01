"""Dual-authority, one-shot execution for the frozen historical ATTD sample.

Only :func:`execute_historical_validation_sample_once` can instantiate the
real provider transport. Validation and dry-run paths are strictly offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import traceback
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from gridiron.market.player_td_authorized_execution import (
    _append_existing,
    _LedgerIdentity,
)
from gridiron.market.player_td_event_resolution_authority import (
    event_resolution_destination,
    validate_event_resolution_authority,
)
from gridiron.market.player_td_execution import (
    ExecutionBoundaryError,
    load_strict_json,
    strict_json_loads,
)
from gridiron.market.player_td_historical_authority import (
    historical_raw_destination,
    validate_historical_authority,
)
from gridiron.market.player_td_sample import validate_frozen_sample_manifest

MANIFEST_SHA256 = "b120ac96101f01846906a66eab1987cfa57dbfbbd742e58384fb1f5f4edda927"
ATTD_AUTHORITY_SHA256 = "4f7f3baab797051909c284f30102254e5d9f2f255e30ffb24c077bf984c2dd77"
EVENT_AUTHORITY_SHA256 = "d8136aab1a1915ca99cc1b6cb5bf8bff113ae06fd32c67238423305beebfc980"

REFERENCE_ROOT = Path("data/reference/player_td_sample_v1")
ATTD_AUTHORITY_PATH = REFERENCE_ROOT / "step93j1_historical_authority.json"
EVENT_AUTHORITY_PATH = (
    REFERENCE_ROOT / "step93j1a_historical_event_resolution_authority.json"
)
MANIFEST_PATH = REFERENCE_ROOT / "step93c_player_td_sample_manifest.json"
SCHEDULE_PATH = REFERENCE_ROOT / "player_td_schedule_2023_2025_v1.json"
PROVENANCE_PATH = REFERENCE_ROOT / "schedule_provenance.json"
RESEARCH_ROOT = Path("data/research/player_td_validation/step93c_sample")
RESOLUTION_PATH = RESEARCH_ROOT / "provider_event_resolution.json"
STATE_ROOT = RESEARCH_ROOT / "execution"

DISCOVERY_LIMIT = 3
MARKET_LIMIT = 6
TOTAL_LIMIT = 9
SPORT = "americanfootball_nfl"
DISCOVERY_ENDPOINT = "/v4/historical/sports/americanfootball_nfl/events"
MARKET_ENDPOINT = "/v4/historical/sports/americanfootball_nfl/events/{event_id}/odds"
PROVIDER_EVENT_ID = re.compile(r"[0-9a-f]{32}\Z")


class HistoricalExecutionError(ExecutionBoundaryError):
    """The frozen historical execution failed closed."""


@dataclass(frozen=True)
class HistoricalProviderResult:
    raw_bytes: bytes
    http_status: int
    acquired_at: str


@dataclass(frozen=True)
class DiscoveryRequest:
    canonical_game_id: str
    sport: str
    discovery_date: str
    endpoint: str


@dataclass(frozen=True)
class MarketRequest:
    sample_item_id: str
    canonical_game_id: str
    provider_event_id: str
    sport: str
    requested_snapshot_at: str
    market: str
    region: str
    odds_format: str
    bookmakers: tuple[str, ...]
    endpoint: str


class HistoricalTransport(Protocol):
    def send_discovery_once(
        self, request: DiscoveryRequest, api_key: str
    ) -> HistoricalProviderResult: ...

    def send_market_once(
        self, request: MarketRequest, api_key: str
    ) -> HistoricalProviderResult: ...


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _raw_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load_fixed_inputs(root: Path) -> tuple[dict[str, Any], ...]:
    reference = root / REFERENCE_ROOT
    attd = load_strict_json(reference / ATTD_AUTHORITY_PATH.name)
    event = load_strict_json(reference / EVENT_AUTHORITY_PATH.name)
    manifest = load_strict_json(reference / MANIFEST_PATH.name)
    schedule = load_strict_json(reference / SCHEDULE_PATH.name)
    provenance = load_strict_json(reference / PROVENANCE_PATH.name)
    if not all(isinstance(value, dict) for value in (attd, event, manifest, provenance)):
        raise HistoricalExecutionError("fixed historical artifact schema is invalid")
    validate_historical_authority(attd)
    validate_event_resolution_authority(event)
    validate_frozen_sample_manifest(manifest, schedule, provenance)
    if (
        attd["authority_sha256"] != ATTD_AUTHORITY_SHA256
        or event["authority_sha256"] != EVENT_AUTHORITY_SHA256
        or manifest["manifest_sha256"] != MANIFEST_SHA256
        or attd["manifest_sha256"] != MANIFEST_SHA256
        or event["manifest_sha256"] != MANIFEST_SHA256
        or event["j1_authority_sha256"] != ATTD_AUTHORITY_SHA256
        or attd["execution_enabled"] is not False
        or event["execution_enabled"] is not False
    ):
        raise HistoricalExecutionError("source-pinned historical authority mismatch")
    return attd, event, manifest, schedule, provenance


def _discovery_requests(event: Mapping[str, Any]) -> tuple[DiscoveryRequest, ...]:
    requests = tuple(
        DiscoveryRequest(
            game["canonical_game_id"], SPORT, game["discovery_date"],
            DISCOVERY_ENDPOINT,
        )
        for game in event["games"]
    )
    if len(requests) != DISCOVERY_LIMIT or len({request.canonical_game_id for request in requests}) != DISCOVERY_LIMIT:
        raise HistoricalExecutionError("discovery request scope is invalid")
    return requests


def _market_requests(
    manifest: Mapping[str, Any], event_ids: Mapping[str, str]
) -> tuple[MarketRequest, ...]:
    requests: list[MarketRequest] = []
    for item in manifest["items"]:
        event_id = event_ids.get(item["canonical_game_id"])
        if event_id is None or PROVIDER_EVENT_ID.fullmatch(event_id) is None:
            raise HistoricalExecutionError("provider event resolution is incomplete")
        requests.append(MarketRequest(
            item["sample_item_id"], item["canonical_game_id"], event_id, SPORT,
            item["requested_snapshot_at"], "player_anytime_td", "us", "american",
            ("draftkings", "fanduel", "betmgm"),
            MARKET_ENDPOINT.format(event_id=event_id),
        ))
    if len(requests) != MARKET_LIMIT:
        raise HistoricalExecutionError("market request scope is invalid")
    return tuple(requests)


def _execution_identity() -> str:
    return _digest({
        "manifest_sha256": MANIFEST_SHA256,
        "attd_authority_sha256": ATTD_AUTHORITY_SHA256,
        "event_authority_sha256": EVENT_AUTHORITY_SHA256,
    })


def _paths(root: Path) -> tuple[Path, Path]:
    identity = _execution_identity()
    state_root = root / STATE_ROOT
    return state_root / f"{identity}.jsonl", state_root / f"{identity}.claimed"


def _require_fresh_state(root: Path) -> None:
    state_path, claim_path = _paths(root)
    if (
        state_path.exists()
        or state_path.is_symlink()
        or claim_path.exists()
        or claim_path.is_symlink()
    ):
        raise HistoricalExecutionError("historical execution is already claimed or started")


def _record(previous: Mapping[str, Any], state: str, **details: Any) -> dict[str, Any]:
    base = {
        "sequence": previous["sequence"] + 1,
        "previous_record_sha256": previous["record_sha256"],
        "execution_identity": previous["execution_identity"],
        "manifest_sha256": MANIFEST_SHA256,
        "attd_authority_sha256": ATTD_AUTHORITY_SHA256,
        "event_authority_sha256": EVENT_AUTHORITY_SHA256,
        "state": state,
        **details,
    }
    return {**base, "record_sha256": _digest(base)}


def _initialize_state(root: Path) -> tuple[Path, _LedgerIdentity, list[dict[str, Any]]]:
    state_path, claim_path = _paths(root)
    if state_path.is_symlink() or claim_path.is_symlink():
        raise HistoricalExecutionError("canonical historical state path is unsafe")
    _safe_parent(state_path, root)
    try:
        with claim_path.open("xb", buffering=0) as claim:
            claim.write(_execution_identity().encode())
            os.fsync(claim.fileno())
    except FileExistsError as exc:
        raise HistoricalExecutionError("historical execution is already claimed") from exc
    base = {
        "sequence": 0,
        "previous_record_sha256": "0" * 64,
        "execution_identity": _execution_identity(),
        "manifest_sha256": MANIFEST_SHA256,
        "attd_authority_sha256": ATTD_AUTHORITY_SHA256,
        "event_authority_sha256": EVENT_AUTHORITY_SHA256,
        "state": "AUTHORIZED",
    }
    genesis = {**base, "record_sha256": _digest(base)}
    try:
        with state_path.open("xb", buffering=0) as handle:
            handle.write((_canonical(genesis) + "\n").encode())
            os.fsync(handle.fileno())
            stat = os.fstat(handle.fileno())
    except FileExistsError as exc:
        raise HistoricalExecutionError("historical execution state already exists") from exc
    return state_path, _LedgerIdentity(stat.st_dev, stat.st_ino), [genesis]


def _append_state(
    path: Path,
    identity: _LedgerIdentity,
    records: list[dict[str, Any]],
    state: str,
    **details: Any,
) -> None:
    record = _record(records[-1], state, **details)
    _append_existing(path, identity, records, record)
    records.append(record)


def _assert_safe_destination(path: Path, root: Path) -> None:
    root = root.resolve()
    try:
        relative = path.absolute().relative_to(root)
    except ValueError as exc:
        raise HistoricalExecutionError("evidence destination escapes repository") from exc
    cursor = root
    for part in relative.parts[:-1]:
        cursor = cursor / part
        if cursor.exists() and cursor.is_symlink():
            raise HistoricalExecutionError("evidence path traverses a symlink")
    if path.is_symlink():
        raise HistoricalExecutionError("evidence destination is a symlink")


def _safe_parent(path: Path, root: Path) -> None:
    _assert_safe_destination(path, root)
    path.parent.mkdir(parents=True, exist_ok=True)


def _exclusive_durable_write(path: Path, content: bytes, root: Path) -> None:
    _safe_parent(path, root)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise HistoricalExecutionError("temporary evidence destination is unsafe")
    try:
        with temporary.open("xb", buffering=0) as handle:
            handle.write(content)
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise HistoricalExecutionError("immutable evidence already exists") from exc
    finally:
        if temporary.exists() and not temporary.is_symlink():
            temporary.unlink()


def _write_pair(
    response_path: Path,
    metadata_path: Path,
    raw: bytes,
    metadata: Mapping[str, Any],
    root: Path,
) -> None:
    response_exists = response_path.exists() or response_path.is_symlink()
    metadata_exists = metadata_path.exists() or metadata_path.is_symlink()
    if response_exists != metadata_exists:
        raise HistoricalExecutionError("partial immutable evidence pair exists")
    if response_exists:
        raise HistoricalExecutionError("immutable evidence pair already exists")
    _exclusive_durable_write(response_path, raw, root)
    try:
        _exclusive_durable_write(
            metadata_path, (_canonical(metadata) + "\n").encode(), root
        )
    except Exception as exc:
        raise HistoricalExecutionError("immutable evidence pair is incomplete") from exc


def _require_absent_pair(response_path: Path, metadata_path: Path) -> None:
    response_exists = response_path.exists() or response_path.is_symlink()
    metadata_exists = metadata_path.exists() or metadata_path.is_symlink()
    if response_exists != metadata_exists:
        raise HistoricalExecutionError("partial immutable evidence pair exists")
    if response_exists:
        raise HistoricalExecutionError("immutable evidence pair already exists")


def _preflight_evidence(
    root: Path,
    attd: Mapping[str, Any],
    event: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    resolution = root / RESOLUTION_PATH
    _assert_safe_destination(resolution, root)
    if resolution.exists() or resolution.is_symlink():
        raise HistoricalExecutionError("immutable resolution artifact already exists")
    for game in event["games"]:
        destination = event_resolution_destination(event, game["canonical_game_id"])
        _assert_safe_destination(root / destination.response_path, root)
        _assert_safe_destination(root / destination.metadata_path, root)
        _require_absent_pair(
            root / destination.response_path, root / destination.metadata_path
        )
    for item in manifest["items"]:
        destination = historical_raw_destination(attd, item["sample_item_id"])
        _assert_safe_destination(root / destination.response_path, root)
        _assert_safe_destination(root / destination.metadata_path, root)
        _require_absent_pair(
            root / destination.response_path, root / destination.metadata_path
        )


def _validate_result(result: object) -> HistoricalProviderResult:
    if not isinstance(result, HistoricalProviderResult):
        raise HistoricalExecutionError("transport result is invalid")
    if not isinstance(result.raw_bytes, bytes) or not isinstance(result.http_status, int):
        raise HistoricalExecutionError("transport result is invalid")
    return result


def _match_event(raw: bytes, game: Mapping[str, Any]) -> dict[str, str]:
    try:
        payload = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ExecutionBoundaryError) as exc:
        raise HistoricalExecutionError("historical event response is malformed") from exc
    if not isinstance(payload, Mapping) or not isinstance(payload.get("data"), list):
        raise HistoricalExecutionError("historical event response schema is invalid")
    matches = [
        event for event in payload["data"]
        if isinstance(event, Mapping)
        and event.get("sport_key") == SPORT
        and event.get("home_team") == game["provider_home_team"]
        and event.get("away_team") == game["provider_away_team"]
        and event.get("commence_time") == game["kickoff_at"]
    ]
    if len(matches) != 1:
        raise HistoricalExecutionError("historical event resolution is not unique")
    event = matches[0]
    event_id = event.get("id")
    if not isinstance(event_id, str) or PROVIDER_EVENT_ID.fullmatch(event_id) is None:
        raise HistoricalExecutionError("provider event ID is invalid")
    return {
        "provider_event_id": event_id,
        "provider_commence_time": event["commence_time"],
        "provider_home_team": event["home_team"],
        "provider_away_team": event["away_team"],
    }


def _resolution_artifact(resolutions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    base = {
        "schema_version": 1,
        "artifact_version": "step93j2-provider-event-resolution-v1",
        "event_authority_sha256": EVENT_AUTHORITY_SHA256,
        "attd_authority_sha256": ATTD_AUTHORITY_SHA256,
        "manifest_sha256": MANIFEST_SHA256,
        "games": [dict(value) for value in resolutions],
    }
    return {**base, "artifact_sha256": _digest(base)}


def _write_resolution(root: Path, resolutions: Sequence[Mapping[str, Any]]) -> None:
    path = root / RESOLUTION_PATH
    if path.exists() or path.is_symlink():
        raise HistoricalExecutionError("immutable resolution artifact already exists")
    artifact = _resolution_artifact(resolutions)
    _exclusive_durable_write(path, (_canonical(artifact) + "\n").encode(), root)


def historical_dry_run(*, repository_root: Path | str = Path(".")) -> dict[str, Any]:
    """Validate and report the frozen plan without credentials, state, or I/O writes."""
    root = Path(repository_root)
    attd, event, manifest, _, _ = _load_fixed_inputs(root)
    discoveries = _discovery_requests(event)
    placeholder = {game["canonical_game_id"]: "0" * 32 for game in event["games"]}
    markets = _market_requests(manifest, placeholder)
    state_path, _ = _paths(root)
    return {
        "manifest_sha256": manifest["manifest_sha256"],
        "attd_authority_sha256": attd["authority_sha256"],
        "event_authority_sha256": event["authority_sha256"],
        "discovery_requests": [request.__dict__ for request in discoveries],
        "market_requests": [request.__dict__ for request in markets],
        "discovery_limit": DISCOVERY_LIMIT,
        "market_limit": MARKET_LIMIT,
        "total_limit": TOTAL_LIMIT,
        "state_path": state_path.as_posix(),
        "resolution_path": (root / RESOLUTION_PATH).as_posix(),
        "credential_required_only_for_execution": True,
    }


def _execute_historical_internal_once(
    root: Path,
    transport: HistoricalTransport,
    api_key: str,
) -> tuple[HistoricalProviderResult, ...]:
    if not isinstance(api_key, str) or not api_key:
        raise HistoricalExecutionError("provider credential is unavailable")
    attd, event, manifest, _, _ = _load_fixed_inputs(root)
    discoveries = _discovery_requests(event)
    _require_fresh_state(root)
    _preflight_evidence(root, attd, event, manifest)
    state_path, identity, records = _initialize_state(root)
    _append_state(state_path, identity, records, "STARTED")
    results: list[HistoricalProviderResult] = []
    resolutions: list[dict[str, Any]] = []
    event_ids: dict[str, str] = {}
    try:
        for index, (game, request) in enumerate(
            zip(event["games"], discoveries, strict=True), start=1
        ):
            if index > DISCOVERY_LIMIT:
                raise HistoricalExecutionError("discovery request budget exceeded")
            _append_state(
                state_path, identity, records, "DISCOVERY_ATTEMPTED",
                phase_attempt=index, item_id=request.canonical_game_id,
            )
            result = _validate_result(transport.send_discovery_once(request, api_key))
            results.append(result)
            destination = event_resolution_destination(event, request.canonical_game_id)
            response_path = root / destination.response_path
            metadata_path = root / destination.metadata_path
            raw_sha = _raw_digest(result.raw_bytes)
            metadata = {
                "schema_version": 1,
                "event_authority_sha256": EVENT_AUTHORITY_SHA256,
                "attd_authority_sha256": ATTD_AUTHORITY_SHA256,
                "manifest_sha256": MANIFEST_SHA256,
                "canonical_game_id": request.canonical_game_id,
                "discovery_date": request.discovery_date,
                "acquired_at": result.acquired_at,
                "http_status": result.http_status,
                "sport": SPORT,
                "endpoint_class": "HISTORICAL_EVENTS",
                "raw_sha256": raw_sha,
                "byte_count": len(result.raw_bytes),
                "response_filename": response_path.name,
            }
            _write_pair(response_path, metadata_path, result.raw_bytes, metadata, root)
            if not 200 <= result.http_status < 300:
                raise HistoricalExecutionError("historical discovery HTTP failure")
            matched = _match_event(result.raw_bytes, game)
            event_ids[request.canonical_game_id] = matched["provider_event_id"]
            resolution = {
                "canonical_game_id": request.canonical_game_id,
                "away_team": game["away_team"],
                "home_team": game["home_team"],
                "kickoff_at": game["kickoff_at"],
                "discovery_date": request.discovery_date,
                **matched,
                "raw_response_sha256": raw_sha,
                "acquired_at": result.acquired_at,
            }
            resolutions.append(resolution)
            _append_state(
                state_path, identity, records, "DISCOVERY_SUCCEEDED",
                phase_attempt=index, item_id=request.canonical_game_id,
            )
        _write_resolution(root, resolutions)
        _append_state(state_path, identity, records, "DISCOVERY_COMPLETED")
        markets = _market_requests(manifest, event_ids)
        for index, request in enumerate(markets, start=1):
            if index > MARKET_LIMIT or len(results) >= TOTAL_LIMIT:
                raise HistoricalExecutionError("market request budget exceeded")
            _append_state(
                state_path, identity, records, "MARKET_ATTEMPTED",
                phase_attempt=index, item_id=request.sample_item_id,
            )
            result = _validate_result(transport.send_market_once(request, api_key))
            results.append(result)
            destination = historical_raw_destination(attd, request.sample_item_id)
            response_path = root / destination.response_path
            metadata_path = root / destination.metadata_path
            metadata = {
                "schema_version": 1,
                "attd_authority_sha256": ATTD_AUTHORITY_SHA256,
                "event_authority_sha256": EVENT_AUTHORITY_SHA256,
                "manifest_sha256": MANIFEST_SHA256,
                "sample_item_id": request.sample_item_id,
                "canonical_game_id": request.canonical_game_id,
                "provider_event_id": request.provider_event_id,
                "requested_snapshot_at": request.requested_snapshot_at,
                "acquired_at": result.acquired_at,
                "http_status": result.http_status,
                "market": request.market,
                "region": request.region,
                "odds_format": request.odds_format,
                "bookmakers": list(request.bookmakers),
                "raw_sha256": _raw_digest(result.raw_bytes),
                "byte_count": len(result.raw_bytes),
                "response_filename": response_path.name,
            }
            _write_pair(response_path, metadata_path, result.raw_bytes, metadata, root)
            if not 200 <= result.http_status < 300:
                raise HistoricalExecutionError("historical market HTTP failure")
            _append_state(
                state_path, identity, records, "MARKET_SUCCEEDED",
                phase_attempt=index, item_id=request.sample_item_id,
            )
        _append_state(state_path, identity, records, "COMPLETED")
        return tuple(results)
    except HistoricalExecutionError:
        try:
            _append_state(state_path, identity, records, "FAILED_PARTIAL")
        except ExecutionBoundaryError:
            pass
        raise
    except Exception as exc:
        try:
            _append_state(state_path, identity, records, "FAILED_INDETERMINATE")
        except ExecutionBoundaryError:
            pass
        raise HistoricalExecutionError(
            "provider transport outcome is indeterminate", attempted=len(results) + 1
        ) from exc


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        del req, fp, code, msg, headers, newurl
        return None  # noqa: RET501, PLR1711


class _TransportIndeterminate(RuntimeError):
    pass


def _raise_transport_indeterminate() -> None:
    raise _TransportIndeterminate("provider transport failed") from None


class _OddsAPIHistoricalTransport:
    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(_NoRedirect())

    def _send(
        self, endpoint: str, parameters: Mapping[str, str]
    ) -> HistoricalProviderResult | None:
        query = urllib.parse.urlencode(parameters)
        request = urllib.request.Request(
            f"https://api.the-odds-api.com{endpoint}?{query}", method="GET"
        )
        try:
            try:
                with self._opener.open(request, timeout=60) as response:
                    return HistoricalProviderResult(
                        response.read(), int(response.status), _utc_now()
                    )
            except urllib.error.HTTPError as exc:
                return HistoricalProviderResult(
                    exc.read(), int(exc.code), _utc_now()
                )
        except Exception:  # noqa: BLE001 - all uncertain transport outcomes are terminal
            return None

    def send_discovery_once(
        self, request: DiscoveryRequest, api_key: str
    ) -> HistoricalProviderResult:
        try:
            result = self._send(request.endpoint, {
                "apiKey": api_key,
                "date": request.discovery_date,
                "dateFormat": "iso",
            })
        except Exception:  # noqa: BLE001 - credential boundary must not leak internals
            result = None
        finally:
            api_key = ""
        if result is None:
            del self, request
            _raise_transport_indeterminate()
        return result

    def send_market_once(
        self, request: MarketRequest, api_key: str
    ) -> HistoricalProviderResult:
        try:
            result = self._send(request.endpoint, {
                "apiKey": api_key,
                "date": request.requested_snapshot_at,
                "dateFormat": "iso",
                "markets": request.market,
                "regions": request.region,
                "oddsFormat": request.odds_format,
                "bookmakers": ",".join(request.bookmakers),
            })
        except Exception:  # noqa: BLE001 - credential boundary must not leak internals
            result = None
        finally:
            api_key = ""
        if result is None:
            del self, request
            _raise_transport_indeterminate()
        return result


def _execute_historical_safely(
    root: Path,
    transport: HistoricalTransport,
    api_key: str,
) -> tuple[HistoricalProviderResult, ...]:
    safe_message: str | None = None
    attempted = 0
    try:
        return _execute_historical_internal_once(root, transport, api_key)
    except HistoricalExecutionError as exc:
        safe_message = (
            exc.args[0]
            if len(exc.args) == 1 and isinstance(exc.args[0], str)
            else "historical execution failed"
        )
        attempted = exc.attempted
        if exc.__traceback__ is not None:
            traceback.clear_frames(exc.__traceback__)
    transport = None
    api_key = ""
    if safe_message is not None:
        raise HistoricalExecutionError(safe_message, attempted=attempted) from None
    raise AssertionError("unreachable historical execution state")


def execute_historical_validation_sample_once() -> tuple[HistoricalProviderResult, ...]:
    """Explicitly execute the one canonical historical sample exactly once."""
    _load_fixed_inputs(Path("."))
    api_key = os.environ.get("GRIDIRON_ODDS_API_KEY")
    if not api_key:
        raise HistoricalExecutionError("provider credential is unavailable")
    try:
        return _execute_historical_safely(
            Path("."), _OddsAPIHistoricalTransport(), api_key
        )
    finally:
        api_key = ""


__all__ = [
    "DiscoveryRequest",
    "HistoricalExecutionError",
    "HistoricalProviderResult",
    "MarketRequest",
    "execute_historical_validation_sample_once",
    "historical_dry_run",
]
