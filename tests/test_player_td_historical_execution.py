from __future__ import annotations

import hashlib
import json
import shutil
import types
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import pytest

from gridiron.market import player_td_historical_execution as historical_module
from gridiron.market.player_td_acquisition import (
    PlayerTDAcquisitionError,
    execute_bounded_acquisition,
)
from gridiron.market.player_td_authorized_execution import execute_registered_once
from gridiron.market.player_td_execution import ExecutionBoundaryError
from gridiron.market.player_td_historical_execution import (
    ATTD_AUTHORITY_SHA256,
    EVENT_AUTHORITY_SHA256,
    MANIFEST_SHA256,
    DiscoveryRequest,
    HistoricalExecutionError,
    HistoricalProviderResult,
    MarketRequest,
    _execute_historical_internal_once,
    _execute_historical_safely,
    _load_fixed_inputs,
    _match_event,
    _OddsAPIHistoricalTransport,
    _paths,
    historical_dry_run,
)

REFERENCE = Path("data/reference/player_td_sample_v1")
FIXED_FILES = (
    "step93j1_historical_authority.json",
    "step93j1a_historical_event_resolution_authority.json",
    "step93c_player_td_sample_manifest.json",
    "player_td_schedule_2023_2025_v1.json",
    "schedule_provenance.json",
)
ACQUIRED_AT = "2026-09-29T12:00:00Z"


def repository(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    reference = target / REFERENCE
    reference.mkdir(parents=True)
    for name in FIXED_FILES:
        shutil.copyfile(REFERENCE / name, reference / name)
    return target


def event_payload(game: dict, event_id: str) -> bytes:
    return json.dumps({
        "timestamp": game["discovery_date"],
        "data": [{
            "id": event_id,
            "sport_key": "americanfootball_nfl",
            "commence_time": game["kickoff_at"],
            "home_team": game["provider_home_team"],
            "away_team": game["provider_away_team"],
        }],
    }, separators=(",", ":")).encode()


class FakeTransport:
    def __init__(
        self, root: Path, *, discovery_status: int = 200, market_status: int = 200
    ) -> None:
        self.root = root
        self.discovery_status = discovery_status
        self.market_status = market_status
        self.discovery_calls: list[DiscoveryRequest] = []
        self.market_calls: list[MarketRequest] = []
        self.event_games = json.loads(
            (REFERENCE / "step93j1a_historical_event_resolution_authority.json").read_text()
        )["games"]

    def send_discovery_once(
        self, request: DiscoveryRequest, api_key: str
    ) -> HistoricalProviderResult:
        assert api_key == "test-only-key"
        state, _ = _paths(self.root)
        assert json.loads(state.read_text().splitlines()[-1])["state"] == (
            "DISCOVERY_ATTEMPTED"
        )
        self.discovery_calls.append(request)
        index = len(self.discovery_calls)
        return HistoricalProviderResult(
            event_payload(self.event_games[index - 1], f"{index:032x}"),
            self.discovery_status,
            ACQUIRED_AT,
        )

    def send_market_once(
        self, request: MarketRequest, api_key: str
    ) -> HistoricalProviderResult:
        assert api_key == "test-only-key"
        state, _ = _paths(self.root)
        assert json.loads(state.read_text().splitlines()[-1])["state"] == (
            "MARKET_ATTEMPTED"
        )
        self.market_calls.append(request)
        return HistoricalProviderResult(
            b'{"data":[]}', self.market_status, ACQUIRED_AT
        )


class RaisingTransport(FakeTransport):
    def send_discovery_once(self, request, api_key):
        self.discovery_calls.append(request)
        raise RuntimeError("indeterminate")


def reachable_object_graph(root: object) -> list[object]:
    """Return the bounded object graph reachable from an escaping exception."""
    pending = [root]
    reached: list[object] = []
    seen: set[int] = set()
    while pending:
        value = pending.pop()
        if value is None or id(value) in seen:
            continue
        seen.add(id(value))
        reached.append(value)
        if isinstance(value, BaseException):
            pending.extend((
                value.__cause__, value.__context__, value.__traceback__,
                value.args, value.__dict__,
            ))
        elif isinstance(value, types.TracebackType):
            pending.extend((value.tb_next, value.tb_frame))
        elif isinstance(value, types.FrameType):
            if value.f_globals.get("__name__") == historical_module.__name__:
                pending.append(value.f_locals)
        elif isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, (list, tuple, set, frozenset)):
            pending.extend(value)
        for attribute in ("request", "reason", "url", "full_url"):
            try:
                pending.append(getattr(value, attribute))
            except (AttributeError, ValueError):
                pass
    return reached


class SecretBearingOpener:
    def __init__(self, original: BaseException) -> None:
        self.original = original
        self.requests = []

    def open(self, request, timeout):
        del timeout
        self.requests.append(request)
        raise self.original


class FailingHTTPErrorBody:
    def __init__(self, secret: str) -> None:
        self.original = RuntimeError(
            f"https://example.invalid/?apiKey={secret}"
        )

    def read(self):
        raise self.original

    def close(self):
        pass


class HTTPErrorBodyFailureOpener:
    def __init__(self, secret: str) -> None:
        self.body = FailingHTTPErrorBody(secret)
        self.requests = []

    def open(self, request, timeout):
        del timeout
        self.requests.append(request)
        raise urllib.error.HTTPError(
            request.full_url, 500, "synthetic failure", {}, self.body
        )


class CapturingResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        del exc_type, exc, traceback

    def read(self):
        return b'{}'


class CapturingOpener:
    def __init__(self) -> None:
        self.requests = []

    def open(self, request, timeout):
        assert timeout == 60
        self.requests.append(request)
        return CapturingResponse()


def rehash(value: dict, field: str) -> None:
    material = {key: item for key, item in value.items() if key != field}
    value[field] = hashlib.sha256(
        json.dumps(
            material, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def test_strict_dual_authority_and_manifest_loaders_accept_only_pins(tmp_path):
    root = repository(tmp_path)
    attd, event, manifest, _, _ = _load_fixed_inputs(root)
    assert attd["authority_sha256"] == ATTD_AUTHORITY_SHA256
    assert event["authority_sha256"] == EVENT_AUTHORITY_SHA256
    assert manifest["manifest_sha256"] == MANIFEST_SHA256


@pytest.mark.parametrize(
    "name,field,mutation",
    [
        ("step93j1_historical_authority.json", "authority_sha256", ("market", "other")),
        (
            "step93j1a_historical_event_resolution_authority.json",
            "authority_sha256",
            ("sport", "americanfootball_ncaaf"),
        ),
        ("step93c_player_td_sample_manifest.json", "manifest_sha256", ("region", "eu")),
    ],
)
def test_changed_authorities_and_manifest_fail_closed(
    tmp_path, name, field, mutation
):
    root = repository(tmp_path)
    path = root / REFERENCE / name
    value = json.loads(path.read_text())
    value[mutation[0]] = mutation[1]
    rehash(value, field)
    path.write_text(json.dumps(value, separators=(",", ":")))
    with pytest.raises((ExecutionBoundaryError, ValueError)):
        _load_fixed_inputs(root)


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', '{"a":NaN}'])
def test_strict_authority_loader_rejects_duplicate_and_nonfinite(tmp_path, raw):
    root = repository(tmp_path)
    (root / REFERENCE / "step93j1_historical_authority.json").write_text(raw)
    with pytest.raises(ExecutionBoundaryError):
        _load_fixed_inputs(root)


def test_dry_run_is_exact_and_creates_nothing(tmp_path, monkeypatch):
    root = repository(tmp_path)
    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", "must-not-be-read")
    before = sorted(path.relative_to(root) for path in root.rglob("*"))
    plan = historical_dry_run(repository_root=root)
    after = sorted(path.relative_to(root) for path in root.rglob("*"))
    assert before == after
    assert len(plan["discovery_requests"]) == 3
    assert len(plan["market_requests"]) == 6
    assert plan["discovery_limit"] == 3
    assert plan["market_limit"] == 6
    assert plan["total_limit"] == 9
    assert [request["discovery_date"] for request in plan["discovery_requests"]] == [
        "2023-09-07T12:20:00Z",
        "2024-09-05T12:20:00Z",
        "2025-09-04T12:20:00Z",
    ]


def test_environment_and_callers_cannot_replace_trust_roots(tmp_path, monkeypatch):
    root = repository(tmp_path)
    monkeypatch.setenv("GRIDIRON_ATTD_AUTHORITY_SHA256", "f" * 64)
    monkeypatch.setenv("GRIDIRON_EVENT_AUTHORITY_SHA256", "e" * 64)
    plan = historical_dry_run(repository_root=root)
    assert plan["attd_authority_sha256"] == ATTD_AUTHORITY_SHA256
    assert plan["event_authority_sha256"] == EVENT_AUTHORITY_SHA256
    with pytest.raises(TypeError):
        historical_dry_run(repository_root=root, manifest={})
    with pytest.raises(TypeError):
        historical_module.execute_historical_validation_sample_once(
            trusted_hash="f" * 64
        )


def test_exact_event_match_and_adversarial_failures():
    game = json.loads(
        (REFERENCE / "step93j1a_historical_event_resolution_authority.json").read_text()
    )["games"][0]
    exact = event_payload(game, "a" * 32)
    assert _match_event(exact, game)["provider_event_id"] == "a" * 32
    base = json.loads(exact)
    for mutation in ("zero", "multiple", "reversed", "kickoff", "fuzzy"):
        changed = deepcopy(base)
        event = changed["data"][0]
        if mutation == "zero":
            changed["data"] = []
        elif mutation == "multiple":
            changed["data"].append(deepcopy(event))
        elif mutation == "reversed":
            event["home_team"], event["away_team"] = (
                event["away_team"], event["home_team"]
            )
        elif mutation == "kickoff":
            event["commence_time"] = "2023-09-08T00:21:00Z"
        else:
            event["home_team"] = "Kansas City"
        with pytest.raises(HistoricalExecutionError):
            _match_event(json.dumps(changed).encode(), game)


def test_transport_and_public_wrapper_sever_secret_bearing_exception_graph(
    tmp_path, monkeypatch
):
    secret = "TEST_ONLY_SECRET_93J2_R4"
    discovery = DiscoveryRequest(
        canonical_game_id="2023_01_DET_KC",
        sport="americanfootball_nfl",
        discovery_date="2023-09-07T12:20:00Z",
        endpoint="/v4/historical/sports/americanfootball_nfl/events",
    )

    direct_original = urllib.error.URLError(
        f"https://example.invalid/?apiKey={secret}"
    )
    direct_transport = _OddsAPIHistoricalTransport()
    direct_transport._opener = SecretBearingOpener(direct_original)
    with pytest.raises(Exception) as direct_caught:
        direct_transport.send_discovery_once(discovery, secret)
    assert len(direct_transport._opener.requests) == 1
    direct_request = direct_transport._opener.requests[0]
    direct_graph = reachable_object_graph(direct_caught.value)
    assert all(value is not direct_original for value in direct_graph)
    assert all(value is not direct_request for value in direct_graph)
    assert all(
        secret not in value.decode(errors="replace")
        if isinstance(value, bytes)
        else secret not in value
        for value in direct_graph
        if isinstance(value, (str, bytes))
    )

    public_original = urllib.error.URLError(
        f"https://example.invalid/?apiKey={secret}"
    )
    public_transport = _OddsAPIHistoricalTransport()
    public_transport._opener = SecretBearingOpener(public_original)
    with pytest.raises(HistoricalExecutionError) as public_caught:
        _execute_historical_safely(
            repository(tmp_path), public_transport, secret
        )
    assert len(public_transport._opener.requests) == 1
    public_request = public_transport._opener.requests[0]
    public_graph = reachable_object_graph(public_caught.value)
    assert all(value is not public_original for value in public_graph)
    assert all(value is not public_request for value in public_graph)
    assert all(
        secret not in value.decode(errors="replace")
        if isinstance(value, bytes)
        else secret not in value
        for value in public_graph
        if isinstance(value, (str, bytes))
    )

    monkeypatch.setenv("GRIDIRON_ODDS_API_KEY", secret)
    monkeypatch.setattr(historical_module, "_load_fixed_inputs", lambda root: None)
    monkeypatch.setattr(historical_module, "_OddsAPIHistoricalTransport", object)

    def sanitized_failure(root, transport, api_key):
        del root, transport, api_key
        raise HistoricalExecutionError(
            "provider transport outcome is indeterminate", attempted=1
        )

    monkeypatch.setattr(
        historical_module, "_execute_historical_safely", sanitized_failure
    )
    with pytest.raises(HistoricalExecutionError) as entry_caught:
        historical_module.execute_historical_validation_sample_once()
    entry_graph = reachable_object_graph(entry_caught.value)
    assert all(
        secret not in value.decode(errors="replace")
        if isinstance(value, bytes)
        else secret not in value
        for value in entry_graph
        if isinstance(value, (str, bytes))
    )


def test_http_error_body_failure_is_sanitized_and_never_resent(tmp_path):
    secret = "TEST_ONLY_SECRET_93J2_R51"
    discovery = DiscoveryRequest(
        canonical_game_id="2023_01_DET_KC",
        sport="americanfootball_nfl",
        discovery_date="2023-09-07T12:20:00Z",
        endpoint="/v4/historical/sports/americanfootball_nfl/events",
    )

    direct_opener = HTTPErrorBodyFailureOpener(secret)
    direct_transport = _OddsAPIHistoricalTransport()
    direct_transport._opener = direct_opener
    with pytest.raises(Exception) as direct_caught:
        direct_transport.send_discovery_once(discovery, secret)
    assert type(direct_caught.value).__name__ == "_TransportIndeterminate"
    assert len(direct_opener.requests) == 1
    direct_request = direct_opener.requests[0]
    direct_graph = reachable_object_graph(direct_caught.value)
    assert all(value is not direct_opener.body.original for value in direct_graph)
    assert all(value is not direct_request for value in direct_graph)
    assert all(
        secret not in value.decode(errors="replace")
        if isinstance(value, bytes)
        else secret not in value
        for value in direct_graph
        if isinstance(value, (str, bytes))
    )

    root = repository(tmp_path)
    public_opener = HTTPErrorBodyFailureOpener(secret)
    public_transport = _OddsAPIHistoricalTransport()
    public_transport._opener = public_opener
    with pytest.raises(HistoricalExecutionError, match="indeterminate") as caught:
        _execute_historical_safely(root, public_transport, secret)
    assert caught.value.attempted == 1
    assert len(public_opener.requests) == 1
    public_request = public_opener.requests[0]
    public_graph = reachable_object_graph(caught.value)
    assert all(value is not public_opener.body.original for value in public_graph)
    assert all(value is not public_request for value in public_graph)
    assert all(
        secret not in value.decode(errors="replace")
        if isinstance(value, bytes)
        else secret not in value
        for value in public_graph
        if isinstance(value, (str, bytes))
    )
    state_path, _ = _paths(root)
    assert json.loads(state_path.read_text().splitlines()[-1])["state"] == (
        "FAILED_INDETERMINATE"
    )

    replay = FakeTransport(root)
    with pytest.raises(HistoricalExecutionError):
        _execute_historical_safely(root, replay, "test-only-key")
    assert replay.discovery_calls == []
    assert replay.market_calls == []


def test_concrete_transport_constructs_only_frozen_provider_requests():
    api_key = "synthetic-test-key"
    opener = CapturingOpener()
    transport = _OddsAPIHistoricalTransport()
    transport._opener = opener
    discovery = DiscoveryRequest(
        canonical_game_id="2023_01_DET_KC",
        sport="americanfootball_nfl",
        discovery_date="2023-09-07T12:20:00Z",
        endpoint="/v4/historical/sports/americanfootball_nfl/events",
    )
    market = MarketRequest(
        sample_item_id="a" * 64,
        canonical_game_id="2023_01_DET_KC",
        provider_event_id="b" * 32,
        sport="americanfootball_nfl",
        requested_snapshot_at="2023-09-07T23:20:00Z",
        market="player_anytime_td",
        region="us",
        odds_format="american",
        bookmakers=("draftkings", "fanduel", "betmgm"),
        endpoint=f"/v4/historical/sports/americanfootball_nfl/events/{'b' * 32}/odds",
    )

    transport.send_discovery_once(discovery, api_key)
    transport.send_market_once(market, api_key)

    assert len(opener.requests) == 2
    discovery_url = urllib.parse.urlsplit(opener.requests[0].full_url)
    market_url = urllib.parse.urlsplit(opener.requests[1].full_url)
    assert (discovery_url.scheme, discovery_url.netloc, discovery_url.path) == (
        "https", "api.the-odds-api.com",
        "/v4/historical/sports/americanfootball_nfl/events",
    )
    assert urllib.parse.parse_qs(discovery_url.query) == {
        "apiKey": [api_key],
        "date": ["2023-09-07T12:20:00Z"],
        "dateFormat": ["iso"],
    }
    assert (market_url.scheme, market_url.netloc, market_url.path) == (
        "https", "api.the-odds-api.com",
        f"/v4/historical/sports/americanfootball_nfl/events/{'b' * 32}/odds",
    )
    assert urllib.parse.parse_qs(market_url.query) == {
        "apiKey": [api_key],
        "date": ["2023-09-07T23:20:00Z"],
        "dateFormat": ["iso"],
        "markets": ["player_anytime_td"],
        "regions": ["us"],
        "oddsFormat": ["american"],
        "bookmakers": ["draftkings,fanduel,betmgm"],
    }


def test_malformed_discovery_is_retained_and_never_resent(tmp_path):
    class MalformedDiscoveryTransport(FakeTransport):
        def send_discovery_once(self, request, api_key):
            assert api_key == "test-only-key"
            self.discovery_calls.append(request)
            return HistoricalProviderResult(b"{malformed", 200, ACQUIRED_AT)

    root = repository(tmp_path)
    transport = MalformedDiscoveryTransport(root)
    with pytest.raises(HistoricalExecutionError, match="malformed"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert len(transport.discovery_calls) == 1
    assert transport.market_calls == []
    retained = [
        path for path in (root / "data/research").rglob("*")
        if path.is_file() and path.read_bytes() == b"{malformed"
    ]
    assert len(retained) == 1

    replay = FakeTransport(root)
    with pytest.raises(HistoricalExecutionError):
        _execute_historical_internal_once(root, replay, "test-only-key")
    assert replay.discovery_calls == []
    assert replay.market_calls == []


def test_complete_execution_uses_three_then_six_and_preserves_evidence(tmp_path):
    root = repository(tmp_path)
    transport = FakeTransport(root)
    results = _execute_historical_internal_once(root, transport, "test-only-key")
    assert len(results) == 9
    assert len(transport.discovery_calls) == 3
    assert len(transport.market_calls) == 6
    assert [request.provider_event_id for request in transport.market_calls] == [
        "0" * 31 + "1", "0" * 31 + "1",
        "0" * 31 + "2", "0" * 31 + "2",
        "0" * 31 + "3", "0" * 31 + "3",
    ]
    resolution = json.loads(
        (root / "data/research/player_td_validation/step93c_sample/"
         "provider_event_resolution.json").read_text()
    )
    assert len(resolution["games"]) == 3
    for response in root.rglob("*.response.json"):
        metadata = json.loads(response.with_name(
            response.name.replace(".response.json", ".metadata.json")
        ).read_text())
        assert metadata["raw_sha256"] == hashlib.sha256(response.read_bytes()).hexdigest()
        assert metadata["byte_count"] == len(response.read_bytes())
    ledger, _ = _paths(root)
    states = [json.loads(line)["state"] for line in ledger.read_text().splitlines()]
    assert states.index("DISCOVERY_COMPLETED") < states.index("MARKET_ATTEMPTED")
    assert states[-1] == "COMPLETED"


def test_replay_is_zero_call(tmp_path):
    root = repository(tmp_path)
    first = FakeTransport(root)
    _execute_historical_internal_once(root, first, "test-only-key")
    replay = FakeTransport(root)
    with pytest.raises(HistoricalExecutionError, match="claimed"):
        _execute_historical_internal_once(root, replay, "test-only-key")
    assert replay.discovery_calls == replay.market_calls == []


def test_discovery_http_failure_stops_before_market_and_does_not_retry(tmp_path):
    root = repository(tmp_path)
    transport = FakeTransport(root, discovery_status=500)
    with pytest.raises(HistoricalExecutionError, match="HTTP"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert len(transport.discovery_calls) == 1
    assert transport.market_calls == []


def test_indeterminate_discovery_is_never_resent(tmp_path):
    root = repository(tmp_path)
    transport = RaisingTransport(root)
    with pytest.raises(HistoricalExecutionError, match="indeterminate"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert len(transport.discovery_calls) == 1
    assert transport.market_calls == []
    replay = FakeTransport(root)
    with pytest.raises(HistoricalExecutionError, match="claimed"):
        _execute_historical_internal_once(root, replay, "test-only-key")
    assert replay.discovery_calls == []


def test_existing_partial_conflicting_and_symlink_evidence_fail_closed(tmp_path):
    root = repository(tmp_path)
    event_root = root / "data/research/player_td_validation/step93c_sample/event_resolution"
    event_root.mkdir(parents=True)
    partial = event_root / "2023_01_det_kc.response.json"
    partial.write_bytes(b"different")
    transport = FakeTransport(root)
    with pytest.raises(HistoricalExecutionError, match="partial"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert transport.discovery_calls == []
    assert transport.market_calls == []


def test_existing_full_evidence_pair_fails_before_transport(tmp_path):
    root = repository(tmp_path)
    event_root = root / "data/research/player_td_validation/step93c_sample/event_resolution"
    event_root.mkdir(parents=True)
    (event_root / "2023_01_det_kc.response.json").write_text("malformed")
    (event_root / "2023_01_det_kc.metadata.json").write_text("{}")
    transport = FakeTransport(root)
    with pytest.raises(HistoricalExecutionError, match="already exists"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert transport.discovery_calls == transport.market_calls == []


def test_symlink_evidence_substitution_fails_before_transport(tmp_path, monkeypatch):
    root = repository(tmp_path)
    original = Path.is_symlink
    original_exists = Path.exists
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: self.name == "event_resolution" or original(self),
    )
    monkeypatch.setattr(
        Path,
        "exists",
        lambda self: self.name == "event_resolution" or original_exists(self),
    )
    transport = FakeTransport(root)
    with pytest.raises(HistoricalExecutionError, match="symlink"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert transport.discovery_calls == transport.market_calls == []


def test_resolution_conflict_prevents_market_phase(tmp_path):
    root = repository(tmp_path)
    result = root / "data/research/player_td_validation/step93c_sample/"
    result.mkdir(parents=True)
    (result / "provider_event_resolution.json").write_text("{}")
    transport = FakeTransport(root)
    with pytest.raises(HistoricalExecutionError, match="resolution"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert transport.discovery_calls == []
    assert transport.market_calls == []


def test_market_http_failure_is_one_attempt_without_retry(tmp_path):
    root = repository(tmp_path)
    transport = FakeTransport(root, market_status=503)
    with pytest.raises(HistoricalExecutionError, match="market HTTP"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert len(transport.discovery_calls) == 3
    assert len(transport.market_calls) == 1


def test_indeterminate_market_is_never_resent(tmp_path):
    root = repository(tmp_path)

    class RaisingMarketTransport(FakeTransport):
        def send_market_once(self, request, api_key):
            self.market_calls.append(request)
            raise RuntimeError("indeterminate")

    transport = RaisingMarketTransport(root)
    with pytest.raises(HistoricalExecutionError, match="indeterminate"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert len(transport.discovery_calls) == 3
    assert len(transport.market_calls) == 1
    replay = FakeTransport(root)
    with pytest.raises(HistoricalExecutionError, match="claimed"):
        _execute_historical_internal_once(root, replay, "test-only-key")
    assert replay.discovery_calls == replay.market_calls == []


def test_concurrent_execution_cannot_duplicate_transport(tmp_path):
    root = repository(tmp_path)
    transports = [FakeTransport(root), FakeTransport(root)]

    def run(transport):
        try:
            return _execute_historical_internal_once(
                root, transport, "test-only-key"
            )
        except HistoricalExecutionError:
            return ()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, transports))
    assert sorted(len(outcome) for outcome in outcomes) == [0, 9]
    assert sum(len(item.discovery_calls) for item in transports) == 3
    assert sum(len(item.market_calls) for item in transports) == 6


def test_missing_credential_fails_before_state_or_transport(tmp_path):
    root = repository(tmp_path)
    transport = FakeTransport(root)
    with pytest.raises(HistoricalExecutionError, match="credential"):
        _execute_historical_internal_once(root, transport, "")
    assert transport.discovery_calls == transport.market_calls == []
    assert not (root / "data/research").exists()


def test_public_entry_missing_credential_cannot_construct_transport(monkeypatch):
    monkeypatch.delenv("GRIDIRON_ODDS_API_KEY", raising=False)

    class ForbiddenTransport:
        def __init__(self):
            raise AssertionError("transport constructed before credential gate")

    monkeypatch.setattr(
        historical_module, "_OddsAPIHistoricalTransport", ForbiddenTransport
    )
    with pytest.raises(HistoricalExecutionError, match="credential"):
        historical_module.execute_historical_validation_sample_once()


def test_deleted_state_during_transport_fails_indeterminate(tmp_path):
    root = repository(tmp_path)

    class DeletingTransport(FakeTransport):
        def send_discovery_once(self, request, api_key):
            result = super().send_discovery_once(request, api_key)
            _paths(self.root)[0].unlink()
            return result

    transport = DeletingTransport(root)
    with pytest.raises(HistoricalExecutionError, match="indeterminate"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert len(transport.discovery_calls) == 1


def test_replaced_state_during_transport_fails_indeterminate(tmp_path):
    root = repository(tmp_path)

    class ReplacingTransport(FakeTransport):
        def send_discovery_once(self, request, api_key):
            result = super().send_discovery_once(request, api_key)
            state = _paths(self.root)[0]
            content = state.read_bytes()
            state.unlink()
            state.write_bytes(content)
            return result

    transport = ReplacingTransport(root)
    with pytest.raises(HistoricalExecutionError, match="indeterminate"):
        _execute_historical_internal_once(root, transport, "test-only-key")
    assert len(transport.discovery_calls) == 1


def test_production_tombstones_remain_zero_call():
    with pytest.raises(ExecutionBoundaryError, match="disabled"):
        execute_registered_once("x", {}, {}, {}, object())
    with pytest.raises(PlayerTDAcquisitionError, match="disabled"):
        execute_bounded_acquisition({}, {}, {}, (), lambda request: request)


def test_no_outcome_model_roi_bet_or_operational_semantics():
    source = Path("src/gridiron/market/player_td_historical_execution.py").read_text()
    assert "data/operational" not in source
    prohibited = ("model fitting", "ROI", "wager recommendation", "TD results")
    assert all(term not in source for term in prohibited)
