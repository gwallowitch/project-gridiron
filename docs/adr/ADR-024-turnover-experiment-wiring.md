# ADR-024: Turnover Experiment Wiring

## Status
Accepted for research wiring.

## Decision
Milestone 65C introduces two independent turnover weights:

- `turnover_int_weight`
- `turnover_fumble_weight`

The turnover feature signs are defined so positive values favor the home team:

- `interception_rate_difference = away INT/game - home INT/game`
- `fumble_lost_rate_difference = away fumbles lost/game - home fumbles lost/game`

Both adjustments are therefore added to the home-centered rating difference.

## Week 1 handling
If either team's prior-turnover history is unknown, both turnover adjustments
are neutral-filled to zero. Week 1 remains in the backtest and uses the existing
model unchanged.

## Research strategy
65C only wires the signals. 65D will test interceptions and lost fumbles
independently before any combined turnover configuration is considered.

## Production boundary
Production turnover weights remain zero.
