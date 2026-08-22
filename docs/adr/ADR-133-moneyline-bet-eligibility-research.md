# ADR-133 — Moneyline Bet-Eligibility Research Foundation

## Status

Accepted for Step 89E.

## Decision

Add a configurable NFL moneyline eligibility research layer under
`gridiron.market`.

Eligibility is evaluated independently for each side of a game using explicit
research thresholds:

- minimum model-versus-market edge
- minimum expected ROI

A side is eligible only when it meets or exceeds every configured threshold.

The resulting immutable records preserve:

- eligibility status
- model-versus-market edge
- expected ROI
- explicit rejection reasons

Threshold boundaries are inclusive. A value exactly equal to a configured
minimum qualifies.

The thresholds are inputs to the evaluation rather than production constants.
This allows later historical research to sweep candidate threshold combinations
without embedding an arbitrary betting policy in the market domain.

## Rejection Reasons

The initial research contract defines:

- `edge_below_minimum`
- `expected_roi_below_minimum`

Multiple rejection reasons may be preserved for the same side.

## Boundaries

Step 89E does not select between home and away sides.

Eligibility is a research classification and is not itself a recommendation to
place a bet.

Step 89E does not implement:

- production betting thresholds
- bet ranking
- conflict resolution between eligible sides
- stake sizing
- Kelly calculations
- bankroll allocation
- weekly portfolio construction
- risk simulation
- sportsbook selection
- automated betting execution

Step 89E does not modify the locked six-weight football model or the Step 88E
temperature calibration contract.
