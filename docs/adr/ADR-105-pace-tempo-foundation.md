# ADR-105 — Pace / Tempo Foundation

Step 82 closed with no weather promotion after forecast-derived wind failed to
preserve the observed-weather signal.

Step 83 therefore moves to an orthogonal team-behavior family: offensive pace
and play volume.

Step 83A builds leakage-safe rolling pregame features from prior games only:

- offensive plays per game;
- seconds to snap, where available;
- tempo index;
- home-away play-volume advantage;
- home-away seconds-to-snap advantage;
- home-away tempo-index advantage.

No experiment weights are introduced in 83A.

The initial rolling window is four games. Week 1 is intentionally unknown.
Current-game play data is shifted out before rolling calculations, preventing
same-game leakage.
