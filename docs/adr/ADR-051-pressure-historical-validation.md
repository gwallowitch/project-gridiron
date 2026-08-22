# ADR-051: Pressure Historical Validation

## Status
Accepted.

## Context
72A created leakage-safe pressure/pass-protection artifacts using the nflverse
QB-hit-or-sack pressure proxy. Before model wiring, the family needs a repeatable
historical quality gate.

## Decision
72B adds a validation script for 2022–2025.

The validator checks:
- artifact existence;
- unique game rows;
- correct season identity;
- known-history coverage;
- non-null coverage for all five matchup features;
- non-zero feature dispersion;
- minimum prior-history depth;
- minimum offensive dropback sample depth;
- minimum pressure-event sample depth.

Default gates:
- home/away known coverage >= 90%;
- feature coverage >= 85%;
- average home history depth >= 5 weeks;
- average home offensive dropbacks >= 50;
- average home offensive pressure events >= 5.

These are data-quality gates, not predictive promotion rules.

## Scope
72B does not modify feature calculations, model weights, or
`config/experiments.toml`. A passing result allows 72C experiment wiring.
