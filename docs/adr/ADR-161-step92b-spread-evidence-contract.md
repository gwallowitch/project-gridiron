# ADR-161: Step 92B spread evidence contract

## Status

Accepted as an isolated, non-prospective contract. It does not activate spread
collection, a spread model, an execution path, or any cloud lane.

## Context

Step 92A found no provenance-complete historical spread dataset. The retained
2025 workbook has useful point, price, and score fields, but lacks authenticated
quote times and contains malformed non-opposing pairs. It cannot be treated as
an execution replay or used to optimize a spread model. Existing Core-Three
normalization nevertheless establishes the three bookmaker identities and the
provider shape needed for a future spread lane.

## Decision

Step 92B defines separate immutable observation and attempt records classified
as non-prospective. The books are exactly BetMGM, FanDuel, and DraftKings. Each
book contributes one main `spreads` market whose atomic offers bind team, point,
and American price. Home and away teams must match the canonical game, and the
points must be finite exact opposites. Alternate-market selection is excluded;
ambiguity fails closed.

Pick'em is canonical numeric `0.0`. Builders normalize negative zero to positive
zero, while persisted negative zero is rejected so it cannot create a second
identity. Prices use the existing Gridiron American-odds rule: integral values
at most -100 or at least +100.

The contract reuses the frozen T12H, T6H, T3H, T1H, and NEAR_KICKOFF windows.
Collection must be strictly pre-kickoff and inside its target window. Every
bookmaker timestamp must be no later than collection and at most ten minutes
old.

Observations preserve canonical game and timing fields, provider/event identity,
raw-response identity, payload hash, parser version, and three ordered book
quotes. Attempts preserve lane, game/target timing, result, sanitized reason,
raw linkage when available, and observation linkage only for success.

Observation and attempt IDs are SHA-256 hashes of canonical JSON. An exact
existing game/target record is an idempotent replay; different content for that
immutable target fails closed and is never overwritten. These fields are
structurally compatible with the raw-checkpoint architecture, but Step 92B does
not register `SPREAD` in production cloud types or alter Firestore.

## Exclusions

This step performs no provider request, real evidence capture, historical
backfill, alternate-line selection, consensus, model math, edge, BET/NO BET,
execution, settlement, CLV, cloud activation, or use of 2026 outcomes. Existing
moneyline, totals, prospective, and cloud behavior remains frozen.
