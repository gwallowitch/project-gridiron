# ADR-108 — Pace/Tempo Grid Repair

The Step 83C diagnostic showed that the problem was not merely weight scale.

Observed feature ranges:

- play-volume advantage: roughly -32 to +24, with p05/p95 around -13/+12;
- seconds-to-snap advantage: identically 0.0 across all four seasons;
- tempo-index advantage: NaN across all four seasons.

Therefore the seconds and tempo subfamilies are not researchable in their
current implementation and are parked.

The surviving play-volume feature has real dispersion, but the original
0.01–0.10 grid was too aggressive for the model's unbounded intermediate
rating-to-probability path. Step 83C is repaired to a conservative volume-only
grid: 0.0005, 0.0010, 0.0025, 0.0050.

This avoids changing or clamping production probability logic merely to
accommodate an experimental feature.
