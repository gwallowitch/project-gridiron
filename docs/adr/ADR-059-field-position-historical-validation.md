# ADR-059: Field Position Historical Validation

## Status
Accepted.

## Context
74A created leakage-safe field-position and hidden-yards artifacts. Before model
wiring, the family needs a repeatable historical quality gate.

## Decision
74B validates the 2022–2025 artifacts for:

- artifact existence;
- unique game rows;
- correct season identity;
- home/away known-history coverage;
- non-null coverage for all five derived features;
- non-zero feature dispersion;
- minimum prior-history depth;
- minimum offensive drive-start sample depth;
- minimum defensive opponent-drive sample depth.

Default gates:
- home/away known coverage >= 90%;
- feature coverage >= 85%;
- average home history depth >= 5 weeks;
- average home offensive drives started >= 40;
- average home defensive opponent drives started >= 40.

These are data-quality gates, not predictive promotion thresholds.

## Scope
74B does not modify field-position calculations, model weights, or
`config/experiments.toml`.

If the quality gate passes, 74C may add experiment wiring.
