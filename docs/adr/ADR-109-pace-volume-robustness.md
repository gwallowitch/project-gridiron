# ADR-109 — Pace-Volume Robustness

Step 83C produced only a very small signal. `pace_volume_0025` ranked first,
but its aggregate improvement rounded to effectively zero and the ordinary
promotion review was INCONCLUSIVE.

That is not enough for promotion.

Step 83D therefore asks a narrower question: is the tiny improvement stable
under nearby weights and leave-one-season-out testing?

The grid spans 0.0010 through 0.0035 around the apparent 0.0025 optimum.

Seconds-to-snap and tempo-index remain parked because their historical
implementations were degenerate/non-finite.

If no candidate improves every LOOSO split, the pace-volume family should be
parked rather than tuned further.
