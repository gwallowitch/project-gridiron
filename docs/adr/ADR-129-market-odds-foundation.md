# ADR-129 — Market Odds Foundation

## Status

Accepted for Step 89A.

## Decision

Add a provider-neutral NFL moneyline domain under `gridiron.market`. An
immutable snapshot preserves game and team identifiers, the provider identifier,
a timezone-aware observation timestamp, and raw home and away American odds.

Pure functions convert each raw price to its implied probability and remove vig
from the two-sided market through proportional normalization. The normalization
result retains both implied probabilities alongside the fair home and away
probabilities; it does not overwrite the source prices or intermediate values.

Identifiers, timestamps, and odds are explicitly validated. American odds must
be nonzero integers, including explicit rejection of booleans.

## Boundaries

This layer has no sportsbook-specific integrations, APIs, network calls,
scraping, or API keys. It does not execute bets or implement spreads, totals,
recommendations, stake sizing, or market collection.

Step 89A does not change the locked football model, feature weights, probability
scale, home-field advantage, temperature calibration v1, prediction code, or
historical research results.
