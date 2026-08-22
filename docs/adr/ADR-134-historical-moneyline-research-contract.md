# ADR-134 — Historical Moneyline Research Contract

## Status

Accepted for Step 89F-A.

## Context

Historical betting research requires a reproducible record connecting the market
price observed for an NFL game, the calibrated model probabilities associated
with that observation, and the eventual game outcome.

Recomputing historical probabilities from a future version of the model could
silently change a betting backtest. Historical research therefore needs to
preserve the probabilities used for the observation.

## Decision

Add an immutable `NFLHistoricalMoneylineRecord` under `gridiron.market`.

Each record preserves:

- season
- week
- game identifier
- home and away team identifiers
- market provider identifier
- timezone-aware market observation timestamp
- raw home and away American moneyline odds
- calibrated home and away model probabilities
- winning team identifier

The contract validates identifiers, season and week values, timestamps, raw
American odds, outcome consistency, and calibrated probabilities.

Calibrated home and away probabilities must each be finite and within `[0, 1]`
and must sum to `1.0` within numerical tolerance.

## Research Integrity

Historical calibrated probabilities are stored directly in the record.

They are not recomputed from the current production model during downstream
betting research. This protects historical experiments from accidental model
drift and preserves the exact model-market relationship being evaluated.

Raw market odds are also retained so implied probabilities, vig-free market
probabilities, edge, and expected value can be reproduced by the existing
market-domain functions.

## Boundaries

Step 89F-A defines the historical research contract only.

It does not:

- acquire historical sportsbook data
- choose a sportsbook or odds provider
- call external APIs
- scrape websites
- define closing-line methodology
- define bet eligibility thresholds
- optimize thresholds
- select bets
- size stakes
- allocate bankroll
- simulate weekly portfolios
- execute bets

Step 89F-A does not modify the locked six-weight football model or the Step 88E
temperature calibration contract.
