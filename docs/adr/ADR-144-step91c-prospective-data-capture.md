# ADR-144: Step 91C Prospective Data Capture

## Status

Accepted.

## Context

Step 91B froze the prospective validation protocol. Evaluation must use information
that was genuinely available before kickoff and must not silently replace a missing
decision-time price with a later market value. A durable event history is required
to distinguish the decision from its eventual result.

## Decision

Step 91C records canonical JSON Lines in an append-only ledger. Each game has at most
one `DECISION` and one later `SETTLEMENT`. SHA-256 identities are calculated from
canonical, sorted JSON so the same observation produces the same identity.

The frozen candidate is `market-plus-def-epa-capped-0425-v1`, with market coefficient
`4.980172`, DEF EPA coefficient `1.044827`, intercept `-2.514766`, and symmetric
residual cap `0.0425`. The consensus contains Bet365, SI, Betway, BetMGM, FanDuel,
Caesars, and DraftKings. DraftKings is the execution book.

Only 2026 regular-season games in Weeks 1-16 are accepted. Decisions must precede
kickoff, all seven consensus observations must be present and pre-decision, and only
strictly positive edges become bets. Missing Week 1 DEF EPA is represented as `0.0`;
missing DEF EPA in later weeks rejects the decision. A missing selected execution
price remains an auditable non-bet with null break-even probability and edge.

Settlement references the captured decision and its captured odds. A loss is `-1`
unit, a win uses the captured positive or negative American price, and a non-bet,
push, or cancellation is `0`. An unsettled bet has no profit record and is never
counted as a loss.

The CLI accepts `--ledger PATH` before one of four commands: `capture`, `validate`,
`settle`, or `summary`.

## Consequences

Duplicate decisions, orphan settlements, duplicate settlements, altered identities,
and settlement economics inconsistent with the decision are rejected. Corrections
must be handled explicitly in a later protocol revision; this version never edits or
deletes an accepted event.
