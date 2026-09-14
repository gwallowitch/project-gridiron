# ADR-155: Step 91T closing line, settlement, and CLV

## Status

Accepted as a non-prospective observational audit layer. It does not alter formal Step 91B evidence or any frozen model, market, execution, or collection semantics.

## Decision

The deterministic moneyline close is the valid Step 91P observation for an exact game with the latest actual `collected_at` strictly before kickoff. Selection uses the hardened Step 91P reader. Target labels have no priority over timestamps; manual observations may qualify; absent observations remain unavailable; equal-timestamp contradictory candidates fail closed. No price is fetched, reconstructed, interpolated, backfilled, or substituted.

A recommendation is not an execution. Only an explicit append-only `NON_PROSPECTIVE_RECORDED_EXECUTION` record—with game, pre-kickoff timestamp, HOME/AWAY side, American odds, positive stake, currency, source book, and optional Step 91P observation identity—represents a factual user-entered execution.

No trustworthy automated production final-result source is established for this non-prospective lane. Step 91T therefore defines and tests a typed `FINAL` result boundary, while production result ingestion and automatic settlement remain intentionally unavailable. Arbitrary scraping, schedule scores, and Odds API scores are not authorized sources.

Moneyline settlement supports HOME/AWAY wins and losses and a genuine tied final as PUSH. A win at positive odds `+A` earns `stake × A / 100`; a win at negative odds `-A` earns `stake × 100 / abs(A)`; a loss is `-stake`; a push is zero.

CLV never uses the game outcome. For the executed side, DraftKings CLV is `closing DraftKings break-even probability − execution break-even probability`. Consensus CLV is `closing three-book no-vig probability − execution break-even probability`. Positive values mean the execution beat the close; neither measure is expected profit or a recommendation threshold. Without a close, settlement remains possible but CLV is explicitly unavailable.

Settlement rows are deterministic, semantically replay-validated, bound to the execution, final-result input, and closing observation when available, and append-only with at most one settlement per execution. Existing operational evidence is never rewritten.

The same latest-valid-actual-pre-kickoff rule may later be applied to Step 91R totals observations. Totals settlement, prediction, CLV, and profitability are out of scope. No 2026 outcome may drive model, feature, cap, threshold, book, timing, execution, or candidate changes.
