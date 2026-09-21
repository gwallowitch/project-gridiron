"""Build or audit the blinded Step 92E historical spread sample offline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gridiron.market.historical_spread_manifest import (
    HistoricalManifestError,
    build_historical_manifest,
    estimate_cost,
    manifest_json,
    validate_historical_manifest,
)
from gridiron.market.historical_spreads import (
    HistoricalSpreadError,
    audit_historical_records,
    parse_saved_historical_snapshot,
)


def _json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    manifest = commands.add_parser("build-manifest")
    manifest.add_argument("--schedule", required=True, type=Path)
    manifest.add_argument("--credits-per-request", type=int, default=10)
    audit = commands.add_parser("audit-saved-sample")
    audit.add_argument("--manifest", required=True, type=Path)
    audit.add_argument("--sample-directory", required=True, type=Path)
    return parser


def _build(schedule: Path, credits: int) -> int:
    games = _json(schedule)
    if not isinstance(games, list):
        raise HistoricalManifestError("schedule must be a JSON array")
    manifest = build_historical_manifest(games)
    cost = estimate_cost(len(manifest["items"]), credits_per_request=credits)
    print(manifest_json({"manifest": manifest, "cost_estimate": cost}))
    return 0


def _audit(manifest_path: Path, sample_directory: Path) -> int:
    manifest = _json(manifest_path)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("items"), list):
        raise HistoricalSpreadError("MALFORMED_MANIFEST")
    validate_historical_manifest(manifest)
    records = []
    malformed = 0
    for item in manifest["items"]:
        item_id = item["manifest_item_id"]
        payload_path = sample_directory / f"{item_id}.json"
        metadata_path = sample_directory / f"{item_id}.metadata.json"
        if not payload_path.exists() and not metadata_path.exists():
            continue
        try:
            raw = payload_path.read_bytes()
            payload = json.loads(raw)
            metadata = _json(metadata_path)
            if not isinstance(metadata, dict):
                raise HistoricalSpreadError("MALFORMED_METADATA")
            records.append(
                parse_saved_historical_snapshot(
                    payload, raw, metadata, item,
                    expected_manifest_sha256=manifest["manifest_sha256"],
                )
            )
        except (OSError, KeyError, json.JSONDecodeError, HistoricalSpreadError):
            malformed += 1
    report = audit_historical_records(records)
    report["manifest_sha256"] = manifest["manifest_sha256"]
    report["requested_observations"] = len(manifest["items"])
    report["malformed_payload_count"] = malformed
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if malformed == 0 else 2


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "build-manifest":
            return _build(args.schedule, args.credits_per_request)
        return _audit(args.manifest, args.sample_directory)
    except (OSError, json.JSONDecodeError, HistoricalManifestError, HistoricalSpreadError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
