from __future__ import annotations

import inspect
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from gridiron.market.historical_spread_manifest import (
    BOOKMAKER_KEYS,
    HistoricalManifestError,
    build_historical_manifest,
    estimate_cost,
    manifest_json,
    validate_historical_manifest,
)
from gridiron.market.historical_spreads import (
    HistoricalSpreadError,
    audit_historical_records,
    build_raw_artifact_metadata,
    parse_saved_historical_snapshot,
)
from scripts.gridiron_historical_spread_audit import main as audit_cli

KICKOFF = datetime(2023, 9, 17, 17, tzinfo=UTC)


def game(season=2023, week=2, suffix="A", kickoff=KICKOFF, season_type="REG"):
    return {
        "game_id": f"{season}_{week:02d}_AW{suffix}_HM{suffix}", "season": season,
        "season_type": season_type, "week": week, "home_team": f"HM{suffix}",
        "away_team": f"AW{suffix}",
        "kickoff_at": kickoff.isoformat().replace("+00:00", "Z"),
    }


def schedule():
    rows = []
    for season in (2021, 2023, 2025):
        for week in (2, 8, 15):
            base = datetime(season, 9 if week < 8 else 11, 1, 17, tzinfo=UTC)
            rows.extend((game(season, week, "B", base + timedelta(hours=1)), game(season, week, "A", base)))
        rows.append(game(season, 1, "WC", datetime(season + 1, 1, 10, 17, tzinfo=UTC), "WC"))
    return rows


def fixture():
    manifest = build_historical_manifest(schedule())
    item = next(row for row in manifest["items"] if row["season"] == 2023 and row["week"] == 2 and row["target_label"] == "T1H")
    target = datetime.fromisoformat(item["target_timestamp"])
    snapshot = target - timedelta(minutes=5)
    books = []
    for key in BOOKMAKER_KEYS:
        books.append(
            {
                "key": key, "last_update": (snapshot - timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
                "markets": [{
                    "key": "spreads", "last_update": (snapshot - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
                    "outcomes": [
                        {"name": item["away_team"], "point": 3.5, "price": -112},
                        {"name": item["home_team"], "point": -3.5, "price": -108},
                    ],
                }],
            }
        )
    payload = {
        "timestamp": snapshot.isoformat().replace("+00:00", "Z"),
        "data": [{"id": "provider-event-1", "commence_time": item["kickoff_at"],
                  "home_team": item["home_team"], "away_team": item["away_team"],
                  "bookmakers": books}],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    metadata = build_raw_artifact_metadata(
        raw, item, manifest_sha256=manifest["manifest_sha256"],
        acquired_at=datetime(2026, 9, 21, tzinfo=UTC), http_status=200,
        returned_snapshot_timestamp=payload["timestamp"],
    )
    return manifest, item, payload, raw, metadata


def parse(mutator=None):
    manifest, item, payload, raw, metadata = fixture()
    if mutator:
        mutator(manifest, item, payload, metadata)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        metadata["raw_artifact_sha256"] = __import__("hashlib").sha256(raw).hexdigest()
    return parse_saved_historical_snapshot(payload, raw, metadata, item, expected_manifest_sha256=manifest["manifest_sha256"])


def test_manifest_is_deterministic_blinded_bounded_and_hashed():
    first = build_historical_manifest(schedule())
    assert first == build_historical_manifest(list(reversed(schedule())))
    assert len(first["items"]) == 105
    assert len({row["manifest_item_id"] for row in first["items"]}) == 105
    assert manifest_json(first) == manifest_json(first)
    text = manifest_json(first).lower()
    assert not any(field in text for field in ("final_home_score", "winner", "ats_margin", "roi", "profit"))
    validate_historical_manifest(first)


def test_manifest_and_item_mutations_fail_identity_validation():
    manifest = build_historical_manifest(schedule())
    changed = deepcopy(manifest)
    changed["items"][0]["home_team"] = "OTHER"
    with pytest.raises(HistoricalManifestError, match="item identity"):
        validate_historical_manifest(changed)
    changed = deepcopy(manifest)
    changed["sample_rule"] = "changed"
    with pytest.raises(HistoricalManifestError, match="manifest hash"):
        validate_historical_manifest(changed)


def test_outcome_fields_fail_closed():
    rows = schedule()
    rows[0]["final_home_score"] = 20
    with pytest.raises(HistoricalManifestError, match="outcome"):
        build_historical_manifest(rows)


def test_sample_order_uses_kickoff_then_game_id():
    rows = schedule() + [game(2023, 2, "LATE", KICKOFF + timedelta(days=1))]
    ids = {item["canonical_game_id"] for item in build_historical_manifest(rows)["items"] if item["season"] == 2023 and item["week"] == 2}
    assert game(2023, 2, "LATE", KICKOFF + timedelta(days=1))["game_id"] not in ids


def test_valid_snapshot_preserves_atomic_prices_timestamps_and_lag():
    row = parse()
    assert row["target_lag_seconds"] == 300
    assert all(book["accepted"] for book in row["books"])
    assert row["books"][0]["home_price"] == -108
    assert row["books"][0]["home_points"] == -3.5
    assert row["books"][0]["quote_age_at_target_seconds"] == 360


def test_reversed_outcomes_are_team_mapped_and_unrelated_book_ignored():
    def mutate(_m, _i, payload, _md):
        payload["data"][0]["bookmakers"][0]["markets"][0]["outcomes"].reverse()
        payload["data"][0]["bookmakers"].append({"key": "other", "markets": []})
    assert parse(mutate)["books"][0]["home_team"].startswith("HM")


@pytest.mark.parametrize("key", BOOKMAKER_KEYS)
def test_each_missing_book_is_classified_independently(key):
    def mutate(_m, _i, payload, _md):
        payload["data"][0]["bookmakers"] = [book for book in payload["data"][0]["bookmakers"] if book["key"] != key]
    row = parse(mutate)
    missing = next(book for book in row["books"] if book["bookmaker_key"] == key)
    assert missing["rejection_reason"] == "MISSING_BOOK"


@pytest.mark.parametrize("case,reason", [
    ("nonopposing", "NON_OPPOSING_POINTS"), ("badprice", "INVALID_PRICE"),
    ("missingtime", "bookmaker_last_update must be an ISO-8601 timestamp"),
    ("duplicate", "AMBIGUOUS_MAIN_LINE"),
])
def test_market_integrity_failures_are_classified(case, reason):
    def mutate(_m, _i, payload, _md):
        book = payload["data"][0]["bookmakers"][0]
        market = book["markets"][0]
        if case == "nonopposing": market["outcomes"][0]["point"] = 2.5
        elif case == "badprice": market["outcomes"][0]["price"] = 50
        elif case == "missingtime": market.pop("last_update"); book.pop("last_update")
        else: book["markets"].append(deepcopy(market))
    assert parse(mutate)["books"][0]["rejection_reason"] == reason


def test_positive_zero_is_canonical_and_negative_zero_fails_closed():
    def mutate(_m, _i, payload, _md):
        outcomes = payload["data"][0]["bookmakers"][0]["markets"][0]["outcomes"]
        outcomes[0]["point"], outcomes[1]["point"] = 0.0, 0.0
    row = parse(mutate)
    assert row["books"][0]["home_points"] == 0.0

    def negative(_m, _i, payload, _md):
        outcomes = payload["data"][0]["bookmakers"][0]["markets"][0]["outcomes"]
        outcomes[0]["point"], outcomes[1]["point"] = 0.0, -0.0
    assert parse(negative)["books"][0]["rejection_reason"] == "NEGATIVE_ZERO_NOT_CANONICAL"


@pytest.mark.parametrize("position,reason", [
    ("after_snapshot", "QUOTE_AFTER_SNAPSHOT"),
    ("at_kickoff", "QUOTE_AT_OR_AFTER_KICKOFF"),
    ("after_kickoff", "QUOTE_AT_OR_AFTER_KICKOFF"),
])
def test_impossible_quote_times_reject(position, reason):
    def mutate(_m, item, payload, _md):
        if position == "after_snapshot": stamp = datetime.fromisoformat(payload["timestamp"]) + timedelta(seconds=1)
        elif position == "at_kickoff": stamp = datetime.fromisoformat(item["kickoff_at"])
        else: stamp = datetime.fromisoformat(item["kickoff_at"]) + timedelta(seconds=1)
        payload["data"][0]["bookmakers"][0]["markets"][0]["last_update"] = stamp.isoformat().replace("+00:00", "Z")
    assert parse(mutate)["books"][0]["rejection_reason"] == reason


def test_snapshot_after_target_rejects():
    manifest, item, payload, raw, metadata = fixture()
    payload["timestamp"] = (datetime.fromisoformat(item["target_timestamp"]) + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    raw = json.dumps(payload).encode(); metadata["raw_artifact_sha256"] = __import__("hashlib").sha256(raw).hexdigest(); metadata["returned_snapshot_timestamp"] = payload["timestamp"]
    with pytest.raises(HistoricalSpreadError, match="SNAPSHOT_AFTER_TARGET"):
        parse_saved_historical_snapshot(payload, raw, metadata, item, expected_manifest_sha256=manifest["manifest_sha256"])


@pytest.mark.parametrize("kind,reason", [("raw", "RAW_SHA_MISMATCH"), ("manifest", "MANIFEST_SHA_MISMATCH"), ("item", "MANIFEST_ITEM_MISMATCH")])
def test_provenance_mismatch_rejects(kind, reason):
    manifest, item, payload, raw, metadata = fixture()
    if kind == "raw": raw += b" "
    elif kind == "manifest": metadata["manifest_sha256"] = "0" * 64
    else: metadata["manifest_item_id"] = "0" * 64
    with pytest.raises(HistoricalSpreadError, match=reason):
        parse_saved_historical_snapshot(payload, raw, metadata, item, expected_manifest_sha256=manifest["manifest_sha256"])


def test_request_timestamp_and_http_status_must_match():
    for field, value, reason in (
        ("requested_historical_timestamp", "2020-01-01T00:00:00Z", "REQUEST_TIMESTAMP_MISMATCH"),
        ("http_status", 500, "HTTP_STATUS_INVALID"),
    ):
        manifest, item, payload, raw, metadata = fixture()
        metadata[field] = value
        with pytest.raises(HistoricalSpreadError, match=reason):
            parse_saved_historical_snapshot(payload, raw, metadata, item, expected_manifest_sha256=manifest["manifest_sha256"])


def test_event_team_and_kickoff_mismatches_reject():
    for field in ("home_team", "away_team", "commence_time"):
        manifest, item, payload, raw, metadata = fixture()
        payload["data"][0][field] = "wrong"
        raw = json.dumps(payload).encode(); metadata["raw_artifact_sha256"] = __import__("hashlib").sha256(raw).hexdigest()
        with pytest.raises(HistoricalSpreadError, match="EVENT_IDENTITY_MISMATCH"):
            parse_saved_historical_snapshot(payload, raw, metadata, item, expected_manifest_sha256=manifest["manifest_sha256"])


def test_parser_replay_is_deterministic_and_audit_is_quality_only():
    row = parse()
    assert parse() == row
    report = audit_historical_records([row])
    assert report["readiness"] == "HISTORICAL_SAMPLE_AUDIT_PARTIAL"
    assert report["all_three_books_complete"] == 1
    serialized = json.dumps(report).lower()
    assert not any(word in serialized for word in ("ats", "roi", "profit", "cover"))


def test_empty_sample_remains_not_acquired():
    assert audit_historical_records([])["readiness"] == "HISTORICAL_SAMPLE_NOT_ACQUIRED"


def test_cost_estimator_is_pure_and_configurable():
    assert estimate_cost(105, credits_per_request=10, plan_credit_allowance=2000) == {
        "request_count": 105, "credits_per_request": 10,
        "estimated_total_credits": 1050, "plan_credit_allowance": 2000,
        "allowance_covers_estimate": True, "plan_price": None,
    }


def test_offline_components_have_no_network_imports():
    import gridiron.market.historical_spread_manifest as manifest_module
    import gridiron.market.historical_spreads as parser_module
    source = inspect.getsource(manifest_module) + inspect.getsource(parser_module)
    assert all(token not in source for token in ("requests", "httpx", "urllib", "socket", "GRIDIRON_ODDS_API_KEY"))


def test_raw_metadata_contains_no_secret_or_request_url_fields():
    _manifest, _item, _payload, _raw, metadata = fixture()
    assert not ({"api_key", "authorization", "headers", "url"} & set(metadata))


def test_cli_builds_manifest_without_provider_access(tmp_path, capsys):
    schedule_path = tmp_path / "schedule.json"
    schedule_path.write_text(json.dumps(schedule()), encoding="utf-8")
    assert audit_cli(["build-manifest", "--schedule", str(schedule_path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output["manifest"]["items"]) == 105
    assert output["cost_estimate"]["estimated_total_credits"] == 1050


def test_cli_empty_saved_sample_reports_not_acquired(tmp_path, capsys):
    manifest = build_historical_manifest(schedule())
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest_json(manifest), encoding="utf-8")
    sample_directory = tmp_path / "samples"
    sample_directory.mkdir()
    assert audit_cli([
        "audit-saved-sample", "--manifest", str(manifest_path),
        "--sample-directory", str(sample_directory),
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["readiness"] == "HISTORICAL_SAMPLE_NOT_ACQUIRED"
    assert output["requested_observations"] == 105
