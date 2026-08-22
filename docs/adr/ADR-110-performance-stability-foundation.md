# ADR-110 — Performance Stability Foundation

Step 83 pace/tempo was rejected after the apparent play-volume signal failed
leave-one-season-out robustness.

Step 84 starts a new orthogonal family: team performance stability.

Step 84A uses final scores from prior games only to derive:

- rolling mean point differential;
- rolling standard deviation of point differential;
- rolling mean absolute margin;
- rolling close-game rate;
- home-away stability advantage;
- home-away recent margin advantage;
- home-away close-game experience advantage.

The current game's final score is shifted out before rolling calculations.
Week 1 is intentionally unknown.

No model weights are introduced in Step 84A. The goal is to establish clean
historical artifacts first.
