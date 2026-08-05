# ADR-007: Rest Weight Experiments

## Status

Accepted

## Decision

Extend the experiment framework with a `rest_weight` parameter. During
experiments only:

`adjusted_rating_difference = rating_difference + rest_advantage * rest_weight`

The production Prediction Engine v2 remains unchanged until a candidate
demonstrates a meaningful improvement in backtesting.

## Candidate range

The initial search evaluates weights from 0.00 through 0.50 in increments
of 0.10.
