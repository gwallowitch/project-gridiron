# ADR-114 — First-Half Form Foundation

Step 84 performance stability was rejected and parked.

Step 85 begins a new feature family focused on early-game team quality rather
than full-game outcome volatility.

Step 85A uses play-by-play from the first two quarters of completed prior games
to derive rolling:

- first-half offensive EPA per play;
- first-half defensive EPA advantage;
- first-half offensive play volume;
- home-away advantages for each metric.

All current-game play-by-play is shifted out before rolling calculations.
Week 1 is intentionally unknown.

No model weights are introduced in Step 85A.
