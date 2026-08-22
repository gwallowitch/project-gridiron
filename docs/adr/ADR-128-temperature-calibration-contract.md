# ADR-128 — Temperature Calibration Contract

## Decision

Adopt temperature scaling as the selected probability-calibration method for
the locked six-weight Project Gridiron model.

Step 88D selected temperature scaling after leave-one-season-out robustness
testing:

- Brier improved in 4/4 seasons;
- log loss improved in 4/4;
- ECE improved in 4/4;
- winner accuracy was unchanged;
- calibration parameters were stable.

## Production contract

The final slope is fitted once on the approved 2022–2025 historical population
after method selection. The resulting parameter is written to
`config/temperature_calibration_v1.json`.

The raw probability remains available. Production consumers should expose a
separate `calibrated_home_win_probability` field.

Temperature scaling is monotonic and has zero intercept, so the 0.5 winner
decision boundary is preserved.

No football feature weight changes in Step 88E.

## Future use

Sportsbook edge calculations, expected value, and weekly bankroll/portfolio
allocation should consume calibrated probabilities rather than raw model
probabilities.
