# ADR-111 — Performance Stability Historical Validation

Step 84A produced complete four-season artifacts with:

- approximately 94.4% known coverage for one-prior-game features;
- approximately 88.8% coverage for rolling standard deviation.

The lower stability coverage is expected. Standard deviation requires two prior
games, so both Week 1 and Week 2 are intentionally unavailable.

Step 84B therefore uses a lower minimum coverage gate for
`stability_advantage` than for recent-margin and close-game features.

The validation gate checks:

- one row per game;
- season integrity;
- Week 1 unknown behavior;
- Week 2 margin availability;
- Week 2 stability unavailability;
- Week 3+ stability availability;
- finite numeric values;
- non-zero feature dispersion;
- explicit no-current-game leakage contract.

A PASS permits Step 84C experiment wiring but does not imply predictive value.
