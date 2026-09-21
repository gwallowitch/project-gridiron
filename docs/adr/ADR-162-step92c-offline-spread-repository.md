# ADR-162: Step 92C offline spread parser and repository

## Status

Accepted as isolated, synthetic-only infrastructure. Step 92C does not create
prospective evidence.

## Decision

An offline parser accepts exactly one caller-supplied provider-shaped event. It
has no HTTP, environment-secret, cloud, Firestore, or scheduler dependency. It
requires exact canonical game orientation, kickoff, optional provider event
identity, and the BetMGM, FanDuel, and DraftKings books. Unrelated books are
ignored but never substituted.

Each required book must have exactly one ordinary `spreads` market and exactly
the expected home and away outcomes. Alternate or duplicate spread markets fail
closed. Team, point, and price remain atomic; no line averaging, consensus,
probability, edge, or decision calculation occurs. Market `last_update` takes
precedence when present, with bookmaker `last_update` as the documented fallback,
matching the retained Core-Three and operational provider patterns. Step 92B
performs final target-window, freshness, point, price, and canonical-zero checks.

Parser failures expose only a deterministic Step 92B reason code. They never
echo the payload, provider URL, headers, credentials, or secret-shaped input.

The isolated repository requires caller-supplied paths and therefore has no
default production evidence destination. It delegates canonical JSONL append,
flush, `fsync`, semantic validation, exact replay, and immutable conflict checks
to the Step 92B contracts. Readers fail closed on malformed, truncated, corrupt,
or contradictory evidence and never repair or rewrite it.

Cross-record validation requires every successful attempt to reference an
existing canonical observation with the same game, target, kickoff, and raw
response identity. Failed attempts require no observation and cannot claim one.
Raw response identity, payload hash, and provider event identity are preserved
unchanged; no raw checkpoint store is created or modified.

## Boundaries

Validation uses synthetic payloads and temporary files only. This step performs
no provider request, real spread capture, historical backfill, cloud activation,
Firestore change, model fitting, consensus, edge, BET/NO BET, settlement, CLV,
or use of 2026 outcomes. The unattended moneyline/totals collector and formal
prospective protocol remain unchanged.
