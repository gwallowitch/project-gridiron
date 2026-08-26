# Step 91D Prospective Market Ingestion for the 2026 Regular Season

Status: DRAFT

## Scope and frozen identity

Step 91D adds six files implementing and documenting a deterministic offline
ingestion boundary. It preserves protocol
`step91b-prospective-validation-v1`, candidate
`market-plus-def-epa-capped-0425-v1`, the seven-book consensus order, and
DraftKings execution. All model calculation and append-only ledger behavior
remain owned by Step 91C.

## Input-to-ledger transformation

The boundary reads one strict JSON snapshot, rejects unknown keys and invalid
types, normalizes timezone-aware timestamps to UTC `Z`, validates the frozen
2026 `REG` Weeks 1-16 window, and accepts only explicit book aliases. It selects
each book's latest observation no later than capture time and emits the seven
observations in Step 91C canonical order. A tied identical latest observation is
collapsed; a conflicting tie, missing book, unexpected book, future observation,
bad price, market mismatch, or team mismatch rejects the entire snapshot.

The selected DraftKings price becomes `execution_prices`. Provider provenance
does not enter the Step 91C payload or event identity. Preview delegates to Step
91C `build_decision()` without touching a ledger; capture validates fully and
delegates to Step 91C `capture_decision()` for one canonical append.

## Operational examples

```text
python scripts/step91d_market_ingestion.py --input snapshot.json preview
python scripts/step91d_market_ingestion.py --input snapshot.json --ledger prospective.jsonl capture
```

Both commands print one compact canonical JSON DECISION. Expected validation
failures print a concise stderr message, return nonzero, and do not emit a
traceback or mutate the ledger.

## Test evidence

The focused Step 91D suite covers strict schema and numeric validation, aliases,
selection and tie behavior, completeness, timing, DEF EPA rules, deterministic
identity, failure atomicity, Step 91C delegation, and both CLI commands. The Step
91C focused suite is rerun separately and together with Step 91D. Exact command
counts and results are recorded in the publication report after verification.

## Limitations

This step provides no scheduler, credentials, live provider, network access,
settlement ingestion, weather changes, dashboard changes, or model
recalibration. Commercial provider selection and live operations remain future
work.
