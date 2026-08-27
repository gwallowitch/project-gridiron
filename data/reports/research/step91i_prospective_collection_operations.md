# Step 91I — Prospective Collection Operations

Status: **READY FOR REAL 2026 COLLECTION**. Real prospective observations: **0**.

The frozen `market-plus-def-epa-capped-0425-v1` candidate and the Step 91B–91H
protocol are unchanged. This layer orchestrates their existing interfaces. It does not
contain another model, consensus calculation, ledger, eligibility rule, or promotion
gate.

## Real game-day procedure

1. Retain the official 2026 REG Week 1–16 schedule as JSON and run `initialize`.
2. Run `summary` and resolve every missing or conflicting canonical game identity.
3. At the predeclared window, retain the provider snapshot and run `capture` with the
   explicit canonical game ID, trusted UTC receipt time, manifest, real ledger, and
   content-addressed artifact directory.
4. Inspect the canonical result. Rejections remain manifest events with deterministic
   reasons. Never edit JSONL. Retries are explicit commands inside the same frozen
   window; an accepted capture cannot be replaced.
5. After the official final result, run `settle` once with its final timestamp and the
   retained official result artifact; the manifest retains its path and SHA256 digest.
6. Run `summary`; investigate missing games, integrity failures, and settlement
   exceptions. Export/publish the Step 91H terminal anchor under the existing process.

Use `python scripts/step91i_collection.py --help` and the `checklist` command for exact
arguments and objective checks. Provider networking is intentionally outside this
repository: the CLI accepts retained inputs through the established Step 91D file
boundary and never invents prices.

## Dry-run boundary

`dry-run --workspace <empty-test-directory>` creates only files beneath that empty,
explicitly isolated directory. Every result is labeled `SYNTHETIC_TEST_DATA`. It
exercises schedule registration, capture, ingestion, DEF EPA Week 1 neutralization,
decision calculation, strict-positive eligibility, trusted receipt, raw hashing,
append-only ledger validation, settlement, chain verification, and summary. It has no
real-ledger argument and cannot populate the real evidence ledger.

## Failure recovery

Interrupted commands are rerun only after inspecting manifest, ledger, and raw hash.
Duplicate games, provider IDs, decisions, and settlements fail. Missing books,
DraftKings, malformed input, stale quotes, invalid DEF EPA, and late capture are
retained as rejected attempts. Postponed, cancelled, and unavailable games receive
explicit status events. Earlier valid decisions are immutable.

## Boundary and limitations

**THIS SYSTEM IS NOW COLLECTING EVIDENCE. IT IS NOT LEARNING FROM THE EVIDENCE
DURING THE COLLECTION PERIOD.** No historical, simulated, reconstructed, or test
observation is real prospective evidence. Provider connectivity remains external;
local receipt timestamps are not external cryptographic chronology; terminal-hash
publication remains an operator responsibility.
