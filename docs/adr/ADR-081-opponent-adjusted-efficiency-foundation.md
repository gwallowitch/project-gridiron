# ADR-081: Opponent-Adjusted Efficiency Foundation

Step 79A creates a leakage-safe opponent-adjusted efficiency family using only
information available before each target game.

The family measures team season-to-date EPA, average quality of prior
opponents, opponent-adjusted offense and defense, and schedule-difficulty
matchup differences.

Matchup features:
- `opponent_adjusted_off_epa_difference`
- `opponent_adjusted_def_epa_difference`
- `offensive_schedule_difficulty_advantage`
- `defensive_schedule_difficulty_advantage`

79A does not modify the experiment grid. Future research must use the promoted
five-weight baseline: rest 0.20, offensive sack 10.00, punt return 0.24,
long-field avoidance 1.00, defensive EPA trend 5.25.
