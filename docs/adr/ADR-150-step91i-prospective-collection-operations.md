# ADR-150: Step 91I Prospective Collection Operations

Status: Accepted

## Context

Steps 91C–91H freeze and audit a prospective protocol but require a repeatable,
operator-safe game-day entry point. Real evidence currently contains zero observations.

## Decision

Add a thin orchestration module and CLI around the existing Step 91H manifest, Step
91D ingestion, and Step 91C append-only ledger. Require canonical scheduled identity,
an explicit trusted receipt time, pre-kickoff/window/freshness validation, seven books,
DraftKings execution, raw SHA256 retention, immediate ledger replay, explicit status
events, and deterministic summaries. Never replace an accepted capture or settlement.

Dry-run has one command, accepts only an empty isolated workspace, creates synthetic
fixtures there, and exposes no real-ledger argument. Output is labeled synthetic.

## Consequences

The correct collection route is short and every failure remains auditable. The module
does no fitting, tuning, backtesting, promotion, or network access. Provider connection,
external chronology proof, and publication of terminal anchors remain operational
limitations outside this repository.

The system collects evidence; it does not learn from that evidence during collection.
