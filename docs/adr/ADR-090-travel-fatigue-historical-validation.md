# ADR-090: Travel Fatigue Historical Validation

Step 81B is the technical gate between the 81A travel foundation and any
experiment wiring.

The gate checks:
- one feature row per scheduled game;
- at least 98% known team geography;
- meaningful travel-mile and time-zone dispersion;
- plausible long-haul and cross-country rates;
- availability of per-team rest-day data;
- neutral-site and international-site schedule indicators.

International and neutral-site games are specifically audited because the 81A
foundation estimates ordinary travel from the away team's home market to the
home team's market. That approximation can be wrong for special-site games.

A PASS permits ordinary travel features to proceed to controlled experiments.
Warnings may still require parking short-week interactions or excluding /
venue-correcting special-site games in Step 81C.
