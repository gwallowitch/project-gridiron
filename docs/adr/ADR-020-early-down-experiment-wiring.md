# ADR-020: Early-Down Experiment Wiring

## Status
Accepted for research wiring.

## Decision
Milestone 64C introduces three independent research weights:

- `early_down_off_weight`
- `early_down_def_weight`
- `early_down_success_weight`

The three signals remain separate so later research can identify whether offense,
defense, success rate, or a combination actually adds predictive value.

The adjustments are additive to the home-centered rating difference:

`rating_difference += off_diff * off_weight`

`rating_difference += def_diff * def_weight`

`rating_difference += success_diff * success_weight`

The 64A feature signs were intentionally constructed so positive values favor
the home team.

## Week 1 handling
When either team's early-down history is unknown, all three early-down
differentials are neutral-filled to zero inside the experiment layer. The game
remains in the backtest and the existing model is used unchanged.

## Production boundary
64C only enables research. No early-down weight is promoted and production
prediction behavior remains unchanged until later research milestones.
