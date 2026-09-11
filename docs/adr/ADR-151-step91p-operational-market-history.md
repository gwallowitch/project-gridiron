# ADR-151: Step 91P Operational Market History

## Status

Accepted for implementation as a non-prospective operational facility.

## Decision

Step 91P stores valid outputs of the existing three-book operational prediction
as canonical JSON Lines in `data/operational/market_history_v1.jsonl`. Records
retain the raw BetMGM, FanDuel, and DraftKings prices and timestamps, canonical
no-vig probabilities, consensus, DEF EPA provenance, frozen model provenance,
and the resulting decision-time values.

This dataset is explicitly classified
`NON_PROSPECTIVE_OPERATIONAL_MARKET_HISTORY`. It is separate from the Step 91B
seven-book protocol, prospective manifest, ledger, and evidence directories.
Writing an operational observation does not create formal prospective evidence.

The file is append-only. Observations for the same game at different capture
timestamps are retained. A SHA-256 identity over canonical record content
rejects an exact retry before writing, preventing a repeated persistence action
from adding the same captured snapshot twice. Existing records are never
rewritten or silently deduplicated.

Reading is fail-closed. A matching content hash is necessary but not sufficient:
every retained row is checked against the immutable Step 91P schema, exact book
set, timestamps, no-vig calculations, consensus, frozen model identity and
coefficients, DraftKings execution calculation, and strict-positive-edge decision
rule. A malformed existing row prevents any later append and is never skipped or
repaired.

Only an already successful operational prediction may be recorded. Missing or
stale books, invalid timestamps, and post-kickoff inputs continue to fail before
persistence. The game-day CLI uses `--record-history` to append the result it
already calculated; persistence performs no provider request.

`OUTSIDE_EARLY_AND_NEAR_KICKOFF_WINDOWS` is informational in the operational
lane: this lane intentionally permits any strictly pre-kickoff prediction. It may
therefore be retained. Existing stale, missing-price, missing-timestamp,
missing-book, or timestamp-after-capture warnings identify invalid market state;
the prediction normally rejects them before persistence, and semantic history
validation rejects them if found in a stored row.

Future closing-line-value research may consume this dataset. CLV calculation,
closing-price collection, background scheduling, and outcome analysis are not
part of Step 91P.

## Step 91P.1 amendment: two-sided execution observation

Step 91P.1 increments the operational-history schema to version 2 and requires
one bounded `two_sided_execution` object in every new row. No schema-version-1
history existed when this amendment was adopted, so the reader rejects version
1 rather than silently accepting incomplete observations. No row is migrated or
rewritten, and completed 2026 games must not be backfilled.

The challenger identity is `two-sided-execution-observation-v1`, classified as
`NON_PROSPECTIVE_TWO_SIDED_EXECUTION_OBSERVATION`. It exists because historical
data lack sufficient decision-time provenance for a credible retrospective
two-sided execution study. It uses only the model probabilities and DraftKings
prices from the same completed in-memory prediction already being retained.
There is no second fetch.

HOME and AWAY edges are independently calculated as model probability minus
that side's DraftKings break-even probability. Positive means strictly greater
than zero. The larger numeric edge is the observational best side; an exact tie
is represented as `TIE` and never defaults to HOME. `both_sides_positive`
retains the unusual but mathematically possible underround case. A missed
opposite-side opportunity is true only when the frozen result is NO BET and the
side opposite its selected side has strictly positive edge.

The frozen directional strategy remains authoritative. Challenger values cannot
change selected side, selected odds, frozen edge, `is_bet`, or the operational
decision. They are non-prospective research observations, not wagering advice.
The reader independently recomputes every challenger field from canonical row
inputs and rejects even correctly re-hashed inconsistencies.

No 2026 result may be used to tune this challenger. Any future evaluation must
compare untouched pre-kickoff observations only after outcomes occur. The
Step 91B protocol, formal candidate, prospective manifest, ledger, and evidence
remain outside this facility and unchanged.
