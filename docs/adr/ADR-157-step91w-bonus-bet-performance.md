# ADR-157: Step 91W bonus-bet execution economics and performance

## Status

Accepted for bounded implementation as non-prospective accounting and
observability infrastructure.

## Decision

Step 91T schema-v1 executions remain immutable legacy `CASH` records with their
original identities and settlement economics. New executions may use schema v2
with an identity-bound `funding_type` of `CASH` or `BONUS_BET`. Unknown types
fail closed. No historical ledger is migrated or rewritten.

Cash settlement remains unchanged: a win earns American-odds profit, a loss is
negative stake, and a push is zero. A Bonus Bet consumes promotional face value,
returns only American-odds winnings as cash on a win, generates zero cash on a
loss, and never counts promotional face value as cash stake or cash loss. Its
conversion rate is cash proceeds divided by settled promotional face value.
A Bonus Bet push fails closed because promotional-token reissue behavior is
sportsbook-policy-dependent and cannot be represented as generic cash.

The read-only reporter validates existing execution and settlement ledgers,
normalizes legacy funding to cash, and reports cash ROI as net cash profit over
settled cash stake. Bonus conversion is separate from cash ROI. Combined realized
cash change is cash-wager net profit plus Bonus Bet cash proceeds; it is not a
sportsbook balance. Reports fail closed rather than aggregate different
currencies. Unsettled executions remain `EXECUTED_AWAITING_RESULT` and are never
losses. `SETTLEMENT_BLOCKED` is not inferred because no authorized result ledger
exists from which to prove that state.

CLV retains Step 91T's probability-space values and sign convention for both
funding types and remains separate from realized return. Reports retain execution,
game, timing, book, odds, side, observation, settlement, result, close, and CLV
provenance when available.

Optional starting cash and bonus values are transient `CALLER_SUPPLIED` inputs.
They are never persisted or represented as independently verified balances.
No promotion-specific terms, scraping, result ingestion, prediction, recommendation,
execution inference, prospective evidence, model optimization, threshold search,
or frozen-model change is introduced.
