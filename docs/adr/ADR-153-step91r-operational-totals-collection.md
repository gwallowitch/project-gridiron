# ADR-153: Step 91R operational totals collection

## Status

Accepted for implementation as an isolated, non-prospective collection lane. Production activation is separate and is not performed by this change.

## Decision

Step 91R records untransformed NFL totals markets from BetMGM, FanDuel, and DraftKings. It produces no projected total, probability, edge, expected value, side selection, betting recommendation, or prospective claim.

Observations and collection attempts use separate append-only files:

- `data/operational/totals_history_v1.jsonl`
- `data/operational/totals_collection_attempts_v1.jsonl`

The collector uses the frozen Step 91Q labels and windows: T12H (660–780 minutes), T6H (330–390), T3H (150–210), T1H (45–75), and NEAR_KICKOFF (5–30). Actual timezone-aware provider and collection timestamps, and the resulting actual minutes before kickoff, are authoritative; a target label cannot replace or override them.

Every successful automatic observation requires an exact scheduled game match, exactly one totals market from each required book, matching Over and Under points, valid American prices, and fresh timestamps no later than collection. Ambiguity, missing data, stale data, malformed retained state, and integrity failures fail closed. No substitute book or prior quote is used.

The observation and attempt logs are hash-identified and append-only. Each automatic game/target is attempted at most once. Failed and missed attempts are retained and are not retried automatically. If an observation append succeeds but its SUCCESS attempt append fails, a later run recognizes only the exact Step 91R automatic provider marker, revalidates the observation and target timing, writes `RECOVERED_SUCCESS`, and makes no provider request or duplicate observation. Manual observations are excluded from recovery.

There is no completed-game backfill. Earlier target windows are recorded as missed only when encountered in normal forward operation; observations are never fabricated or backdated.

## Research-integrity boundary

This lane is `NON_PROSPECTIVE_TOTALS_MARKET_OBSERVATION` infrastructure only. A future totals model is explicitly out of scope. The 2026 outcomes must not be used to optimize the schema, book set, target labels, or timing windows. The frozen moneyline candidate, model mathematics, protocols, operational history, collection attempts, ledger, and evidence paths remain unchanged.
