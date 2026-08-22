# ADR-082: Opponent-Adjusted Historical Validation

## Status
Accepted as the Step 79B technical validation gate.

## Decision
79B validates the 2022–2025 artifacts created by 79A before any experiment
weights are introduced.

The gate checks:
- unique game rows;
- season integrity;
- adequate schedule volume;
- both-team coverage after early-season history develops;
- feature coverage;
- non-zero dispersion;
- non-trivial non-zero observation rates;
- historical week depth;
- opponent sample depth.

## Thresholds
- at least 250 rows per research season;
- at least 85% both-team known coverage from Week 4 onward;
- at least 70% overall coverage per feature;
- positive dispersion;
- at least 50% non-zero observations;
- mean home history depth of at least 5 weeks;
- mean home opponent depth of at least 4 opponents.

A PASS means the family is technically suitable for controlled research. It
does not establish predictive lift.

79C may add isolated experiment configuration support, while preserving the
promoted five-weight baseline from Step 78.
