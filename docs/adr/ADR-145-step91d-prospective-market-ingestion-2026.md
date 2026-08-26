# ADR-145: Step 91D Prospective Market Ingestion for 2026

Status: DRAFT

## Context

Step 91C is the authoritative append-only prospective ledger and frozen model
implementation. Step 91D needs a boundary between externally produced market
snapshots and that ledger without introducing provider availability, credentials,
network behavior, scheduling, or a second implementation of the model.

## Decision

Step 91D is an offline, deterministic, file-ingestion-only boundary. It accepts
one strict JSON object containing schema version 1, provider provenance, capture
time, a 2026 regular-season Week 1-16 game, DEF EPA, and a non-empty offer list.
Unknown or missing keys are rejected at the snapshot, game, and offer levels.
Timestamps must be timezone-aware and are normalized to UTC `Z`; odds must be
integer American prices. Week 1 may retain null DEF EPA for Step 91C's
authoritative conversion to 0.0, while later weeks require a finite number.

Book names are accepted only through the explicit aliases recorded in the Step
91D configuration. For every canonical Step 91C consensus book, ingestion picks
the latest observation at or before `captured_at`. Identical observations tied
at that timestamp collapse; conflicting ties are rejected. All seven books are
required, and missing books are reported in canonical order. Unexpected books,
non-moneyline markets, future observations, and team mismatches are rejected.

The normalized Step 91C payload emits observations in canonical order.
DraftKings' selected observation supplies `execution_prices`. Step 91D delegates
preview to `build_decision()` and capture to `capture_decision()` from Step 91C.
It performs no consensus, probability, residual-cap, edge, identity, validation,
or append calculation of its own.

Provider provenance is validated but intentionally excluded from the Step 91C
payload, so it cannot alter observation or event identity. There are no clock,
random, UUID, filesystem-time, or unordered-iteration inputs. Reordering
semantically identical offers therefore produces identical canonical output.

Validation completes before capture. Raw-input rejection cannot touch a ledger;
Step 91C validates the existing ledger plus the candidate event before its
append, preserving duplicate-decision protection and failure atomicity.

## Consequences and future work

Live-provider selection and integration are deferred until a provider contract,
credentials policy, reliability requirements, and operational controls are
approved. This step adds no network requests, scheduler, settlement ingestion,
weather changes, model recalibration, dashboard changes, or production feed.
