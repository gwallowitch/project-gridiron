# ADR-131 — Moneyline Expected-Value Foundation

## Status

Accepted for Step 89C.

## Decision

Add a pure NFL moneyline expected-value layer under `gridiron.market`.

Expected value is calculated from the production calibrated model probability and
the actual offered American moneyline price.

For a one-unit stake:

`expected_profit = win_probability * profit_if_win - loss_probability`

The resulting immutable record preserves:

- offered American odds
- calibrated model probability
- market implied probability
- profit per unit stake
- expected profit per unit stake
- expected ROI

Expected ROI is numerically equal to expected profit per unit stake because the
stake basis is one unit.

## Boundaries

Step 89C does not use vig-free fair probability to calculate payout economics.
The offered sportsbook price determines the actual payoff.

Step 89C does not implement:

- bet eligibility thresholds
- minimum edge requirements
- minimum expected-value requirements
- bet selection
- Kelly sizing
- bankroll allocation
- weekly portfolio construction
- risk simulation
- automated betting execution

Step 89C does not modify the locked six-weight football model or the Step 88E
temperature calibration contract.
