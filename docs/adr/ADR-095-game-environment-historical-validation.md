# ADR-095 — Game Environment Historical Validation

## Status
Accepted for Step 82B.

## Purpose
Step 82B determines whether the historical game-environment artifacts created
in 82A are technically healthy enough for controlled research.

The gate checks:
- one environment row per game;
- season integrity;
- environment-known coverage;
- temperature and wind coverage;
- temperature and wind dispersion;
- adverse-weather and indoor/roof rates;
- severe-weather examples for manual inspection.

## Leakage contract
Historical observed conditions may be used for exploratory backtesting because
the goal is to discover whether the family contains any signal at all.

However, exact observed conditions are not automatically valid production
inputs. A model used before kickoff cannot rely on values only knowable after
the game has begun or ended.

Therefore:
1. 82B may PASS using historical observed conditions.
2. 82C/82D may screen the family historically.
3. No weather feature may be promoted to production until a later validation
   step demonstrates equivalent behavior using only data available at the
   model decision timestamp.

This preserves research velocity without weakening the no-leakage standard.
