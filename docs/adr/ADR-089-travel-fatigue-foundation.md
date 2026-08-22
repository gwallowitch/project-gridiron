# ADR-089: Travel and Geographic Fatigue Foundation

Step 80 rejected penalty discipline, so the promoted six-weight model remains
the research baseline.

Step 81A creates a new orthogonal feature family based on away-team travel
distance, nominal time-zone shift, travel direction, long-haul/cross-country
flags, and optional short-week travel interactions.

Ordinary away travel is approximated from the away team's home market to the
home team's market using haversine distance. If the existing rest artifact
contains per-team rest-day columns, short-week interactions are created. If it
only exposes rest advantage, those interaction fields remain unknown.

International and neutral-site games are not venue-adjusted in 81A. Step 81B
should audit those outliers before experiment wiring.

Frozen baseline:
- rest = 0.20
- offensive sack = 10.00
- punt return = 0.24
- long-field avoidance = 1.00
- defensive EPA trend = 5.25
- defensive schedule difficulty = 2.25
