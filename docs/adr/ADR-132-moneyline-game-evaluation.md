# ADR-132 — Moneyline Game Evaluation Composition

## Status

Accepted for Step 89D.

## Decision

Add a pure composition layer under `gridiron.market` that combines the existing
moneyline edge and expected-value calculations into one immutable per-game
evaluation record.

The evaluation preserves:

- the full model-versus-market edge record
- home-side expected value
- away-side expected value

The same calibrated model probabilities are passed consistently into both the
edge and expected-value calculations.

This layer does not introduce new pricing math or betting logic. It composes the
Step 89B and Step 89C contracts into a single auditable game-level record.

## Boundaries

Step 89D does not implement:

- bet eligibility
- minimum edge thresholds
- minimum expected-value thresholds
- ranking or selection of bets
- stake sizing
- Kelly calculations
- bankroll allocation
- weekly portfolio construction
- risk simulation
- automated betting execution

Step 89D does not modify the locked six-weight football model or the Step 88E
temperature calibration contract.
