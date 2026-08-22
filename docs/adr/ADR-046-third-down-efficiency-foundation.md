# ADR-046: Third-Down Efficiency Foundation

## Status
Accepted for research foundation.

## Context
Project Gridiron currently carries two promoted/provisional incremental signals:
offensive sack-rate advantage and punt-return advantage. The next research family
should add situational football information rather than another broad efficiency
duplicate.

## Decision
71A introduces leakage-safe pregame third-down efficiency features from
nflverse play-by-play.

Eligible plays:
- down = 3;
- offensive team and defensive team are known;
- play type is run or pass;
- yards-to-go and yards gained are available.

A conversion is defined as `yards_gained >= ydstogo`. Penalty/no-play rows are
therefore not treated as ordinary scrimmage conversions.

Third-and-long is defined as 7 or more yards to go.

Offensive history:
- third-down plays;
- EPA/play;
- conversion rate;
- third-and-long conversion rate;
- third-and-long play count.

Defensive history:
- third-down plays faced;
- EPA/play allowed;
- conversion rate allowed;
- third-and-long conversion rate allowed;
- third-and-long play count faced.

Derived home-centered matchup features:
- `third_down_off_epa_difference`
- `third_down_def_epa_difference`
- `third_down_conversion_difference`
- `third_down_stop_difference`
- `third_and_long_conversion_difference`

## Leakage rule
For a game in week N, only same-season plays from weeks strictly less than N may
contribute. Week 1 therefore has no known same-season history.

## Scope
71A creates, validates, and persists feature artifacts only. It does not modify
experiment weights or the production prediction model.
