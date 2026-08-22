# ADR-064: Fourth-Down Historical Validation

## Status
Accepted.

## Context
75A created leakage-safe fourth-down efficiency artifacts. Fourth-down data is
naturally much sparser than early-down or drive-level data, so its historical
quality gate must distinguish between general fourth-down observations and the
even sparser short-yardage subset.

## Decision
75B validates 2022–2025 artifacts for:

- artifact existence;
- unique game rows;
- season integrity;
- home/away known-history coverage;
- non-null coverage across five derived features;
- non-zero feature dispersion;
- prior-history depth;
- offensive fourth-down attempt depth;
- defensive fourth-down attempt depth.

Default gates:

- home/away known coverage >= 90%;
- generic fourth-down feature coverage >= 85%;
- short-yardage conversion feature coverage >= 70%;
- average prior-history depth >= 4 weeks;
- average offensive fourth-down attempts >= 4;
- average defensive fourth-down attempts faced >= 4.

These gates test data usability, not predictive value.

## Scope
75B does not modify model weights, runtime scoring, or
`config/experiments.toml`.

If the historical gate passes, 75C may add experiment configuration support.
