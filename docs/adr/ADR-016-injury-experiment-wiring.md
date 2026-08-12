# ADR-016: Injury Experiment Wiring

## Status
Accepted for research.

## Decision
Milestone 63B wires `injury_weight` into the experiment and research systems only.

The adjustment is:

`rating_difference = base + rest - injury_score_difference * injury_weight`

where `injury_score_difference = home injury burden - away injury burden`.
Therefore a more injured home roster lowers the home-centered rating.

The experiment grid is 0.00 through 0.50 in 0.10 increments. Rest remains 0.20.
QB remains 0.00 after the 62C rejection.

## Season scope
The `injury_modern` research profile is 2022-2024 only. Verified 2025 nflverse
injury data lacks `date_modified`, so 2025 is excluded from injury-weight research.

## Safety gate
Any non-zero injury experiment requires `source_timestamp_available = true`
for every game in the supplied injury artifact.

## Production boundary
No production prediction constants or promoted model settings change in 63B.
