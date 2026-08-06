# ADR-012: Quarterback Intelligence Foundation

## Status

Accepted

## Decision

Introduce a standalone quarterback feature dataset with:

- home and away starter names;
- home and away quarterback ratings;
- rating difference;
- known/unknown flags.

Missing starter assignments and unknown ratings receive a neutral rating of
zero and the name `UNKNOWN`. This allows the season pipeline to remain
operational before historical starter data is populated.

## Scope boundary

Prediction Engine production behavior does not change in 62A. Quarterback
features must first be evaluated through controlled experiments.
