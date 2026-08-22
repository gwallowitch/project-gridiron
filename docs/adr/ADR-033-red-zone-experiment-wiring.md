# ADR-033: Red-Zone Experiment Wiring

## Status
Accepted for research wiring.

## Decision
Milestone 67C adds four independent red-zone research weights:

- `red_zone_off_epa_weight`
- `red_zone_def_epa_weight`
- `red_zone_success_weight`
- `red_zone_td_rate_weight`

All four feature definitions are home-centered, so positive values favor the
home team. Their weighted adjustments are therefore added to the home-centered
rating difference.

## Missing-history handling
If either team's prior red-zone history is unknown, all four red-zone
adjustments are neutral-filled to zero. Week 1 therefore remains in the
backtest and uses the existing model unchanged.

## Research strategy
67C only enables wiring. 67D will test the four red-zone families
independently before any combined-feature search.

## Production boundary
No red-zone signal is promoted to production in 67C.
