# ADR-087: Penalty Discipline Historical Validation

## Status
Accepted as the Step 80B technical validation gate.

## Decision
80B validates the 2022–2025 penalty-discipline artifacts created by 80A before
any experiment weights are introduced.

The gate checks:
- unique game rows;
- season integrity;
- adequate schedule volume;
- both-team mature coverage from Week 3 onward;
- feature coverage;
- non-zero dispersion;
- non-trivial non-zero observation rates;
- historical week depth;
- offensive and defensive play sample depth.

## Thresholds
- at least 250 rows per research season;
- at least 90% both-team known coverage from Week 3 onward;
- at least 90% overall coverage per feature;
- positive dispersion;
- at least 50% non-zero observations;
- mean history depth of at least 5 weeks;
- mean offensive sample of at least 200 plays;
- mean defensive sample of at least 200 plays.

A PASS means the family is technically suitable for controlled research. It
does not establish predictive lift.

80C may add isolated experiment configuration support while preserving the
promoted six-weight baseline.
