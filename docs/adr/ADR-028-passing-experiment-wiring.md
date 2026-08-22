# ADR-028: Passing Efficiency Experiment Wiring

## Status
Accepted for research wiring.

## Decision
Milestone 66C adds six independent passing research weights:

- `pass_off_epa_weight`
- `pass_def_epa_weight`
- `pass_success_weight`
- `off_sack_weight`
- `def_sack_weight`
- `explosive_pass_weight`

All six underlying feature definitions are home-centered so positive values favor
the home team. Their weighted adjustments are therefore added to the home-centered
rating difference.

## Week 1 handling
If either team's passing history is unknown, all six passing adjustments are
neutral-filled to zero. Week 1 remains in the backtest and uses the existing model
unchanged.

## Research strategy
66C only enables research wiring. 66D will test the six passing families
independently before any combination search is allowed.

## Production boundary
All passing weights remain zero in production until later research supports a
promotion decision.
