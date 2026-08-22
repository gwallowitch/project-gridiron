# ADR-047: Third-Down Historical Validation

## Status
Accepted.

## Context
71A created leakage-safe third-down feature artifacts. Before experiment wiring,
the feature family needs a repeatable historical quality gate rather than a
manual visual-only review.

## Decision
71B adds a validation script for the modern research seasons.

The validator checks:
- artifact existence;
- one row per game;
- correct season value;
- known-history coverage;
- non-null coverage for all five derived matchup features;
- non-zero feature dispersion;
- minimum prior-history depth;
- minimum third-down play sample depth.

Default acceptance thresholds:
- home/away known coverage >= 90%;
- derived feature coverage >= 85%;
- average home history depth >= 5 weeks;
- average home offensive third-down sample >= 20 plays.

These are quality gates, not predictive-promotion thresholds.

## Scope
71B does not change the feature calculations, experiment configuration, model
weights, or current v1 candidate. If the historical validation passes, 71C may
wire third-down fields into the experiment configuration.
