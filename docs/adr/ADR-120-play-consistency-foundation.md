# ADR-120 — Play Consistency Foundation

Step 86 explosive-play rate signals were rejected 0-4 across every tested
candidate.

Step 87 is the final planned standalone feature family before Project Gridiron
pivots from feature discovery into combined-model validation, calibration, and
market work.

Step 87A tests play-level consistency rather than magnitude:

- offensive success rate: EPA > 0 on pass/rush attempts;
- defensive success prevention rate: opponent EPA <= 0;
- offensive negative-play rate: yards gained < 0;
- defensive negative-play rate forced: opponent yards gained < 0.

Pregame values use a four-game rolling window with current-game values shifted
out. Week 1 is intentionally unknown.

The foundation produces both simple home-away differences and matchup-oriented
success/negative-play advantages.

No model weights are introduced in Step 87A.
