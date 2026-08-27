# Step 91G Prospective Protocol Closure and Operational Readiness

## Readiness result

**READY_WITH_DOCUMENTED_LIMITATION**

The frozen Step 91C → 91D → 91F chain can accept the first genuine 2026 observation
without altering the candidate or using historical information. The frozen protocol
and end-to-end integrity audits pass. No prospective evidence currently exists.

## Edge-trim recovery

Repository-local history recovers the predeclared edge-tail definitions:

- exclude the largest 1% positive edges;
- exclude the largest 5% positive edges;
- exclude the largest 10% positive edges.

The published source is `STEP90G_BUILD_PROMPT.md` at commit
`2b83303b679d2c3fbd36bb06508c93d90c819bd9`, replicated unchanged at
`17529d576d0b8b22230c4ab15e31e118f870f310`; both use blob
`393e302347a57ee9bc0d528f4b9b65d177c3aa5b`. Local Git object
`3b9d0a02a9c1d635800bebd6ad6492f164de2610` contains the executable rule: sort
positive edges descending and remove `floor(sample_size × fraction)`.

The limitation is provenance closure: that executable implementation is available
through a local Codex Git ref, not a published frozen Step 91B artifact, and equal-edge
tie semantics are implicit in stable input order. Collection may begin, but Step 91G
does not authorize a future promotion declaration until that limitation is resolved.

## Frozen and end-to-end audit

Candidate identity, coefficients, 4.25% cap, seven books, DraftKings execution,
strictly positive edge, 2026 REG Weeks 1-16, DEF EPA rules, pre-kickoff enforcement,
append-only capture, immutable settlement prices, duplicate/orphan rejection,
retained non-bets, unsettled-bet treatment, and canonical serialization all pass.

## Local gameday runbook

Pre-game:

1. Prepare one strict Step 91D JSON snapshot with game metadata, timezone-aware
   `observed_at`, `captured_at`, and `kickoff_at`, all seven moneyline books, and DEF
   EPA (null only in Week 1).
2. Run `python scripts/step91d_market_ingestion.py --input SNAPSHOT preview`.
3. Run `python scripts/step91f_prospective_evidence.py --ledger LEDGER capture --input SNAPSHOT`.
4. Run `python scripts/step91f_prospective_evidence.py --ledger LEDGER validate`.

Post-game:

1. Run `python scripts/step91f_prospective_evidence.py --ledger LEDGER settle --game-id GAME --result RESULT --settled-at TIMESTAMP`.
2. Validate the ledger again.
3. Run the Step 91F `summary` command and this Step 91G readiness audit.

Exceptions:

- Incomplete market data: reject and wait for a complete contemporaneous snapshot.
- Missing DraftKings execution price: retain the Step 91C observation as a non-bet;
  never substitute a later price. Step 91D raw ingestion requires complete offered
  prices, so a missing raw required price is rejected before capture.
- Missing DEF EPA: Week 1 may remain null; Weeks 2-16 must be rejected.
- Kickoff already occurred: do not capture or backfill.
- Duplicate decision/settlement: preserve the first valid immutable event and
  investigate; do not rewrite it.
- Settlement unavailable: leave the observation unsettled; never count it as a loss.

No live observation, historical backfill, fixture, model change, or threshold invention
is included in this audit.
