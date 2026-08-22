# ADR-130 — Model-Market Edge Foundation

## Status

Accepted for Step 89B.

## Decision

Add a pure NFL moneyline edge layer under `gridiron.market`.

The edge calculation compares the production calibrated model probability with
the vig-free fair market probability derived from the Step 89A moneyline layer.

For each side:

`edge = calibrated_model_probability - fair_market_probability`

The resulting immutable record preserves:

- game and team identifiers
- provider and observation timestamp
- raw home and away American odds
- raw market implied probabilities
- vig-free fair market probabilities
- calibrated model probabilities
- home and away model-market edge

Calibrated home and away probabilities must be finite, each within [0, 1], and
sum to 1.0 within numerical tolerance.

## Boundaries

Step 89B does not define bet eligibility or interpret positive edge as a betting
recommendation.

It does not implement:

- minimum edge thresholds
- expected value
- bet selection
- Kelly sizing
- bankroll allocation
- weekly portfolio construction
- risk simulation
- sportsbook selection
- automated betting execution

Step 89B does not modify the locked six-weight football model or the Step 88E
temperature calibration contract.
