# ADR-055: Neutral Game-State Historical Validation

## Status
Accepted.

## Context
73A created leakage-safe neutral game-state efficiency artifacts. Before adding
weights to the research engine, the family needs a repeatable historical quality
gate.

## Decision
73B validates the 2022–2025 artifacts for:

- artifact existence;
- unique game rows;
- season integrity;
- home/away known-history coverage;
- non-null coverage across all five derived features;
- non-zero feature dispersion;
- minimum prior-history depth;
- minimum neutral-state offensive play depth.

Default gates:
- home/away known coverage >= 90%;
- feature coverage >= 85%;
- average home history depth >= 5 weeks;
- average home offensive neutral-state plays >= 75.

These thresholds test data quality and sample depth. They are not predictive
promotion criteria.

## Scope
73B does not modify neutral-state calculations, model weights, or
`config/experiments.toml`.

If the quality gate passes, 73C may add experiment configuration fields.
