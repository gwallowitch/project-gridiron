# 06 --- Project Gridiron Rating Engine (Normalization)

## Purpose

The normalization layer converts raw football metrics into comparable
rating scores.

Raw metrics such as Offensive EPA per play, Offensive success rate,
Explosive play rate, and Turnover margin exist on different numerical
scales. Before they can be combined into an overall team rating, they
must be normalized.

## Design

The current implementation uses a z-score transformation.

For every metric: 1. Compute the league mean. 2. Compute the league
standard deviation. 3. Convert each team's value to a z-score. 4. Scale
the result to a rating.

Current scale: - League average = 100 - One standard deviation = 10
rating points

Metrics where lower values are better are inverted before scoring.

## Public API

``` python
normalize_metric(frame, column, higher_is_better=True)

normalize_metrics(
    frame,
    {
        "offensive_epa_per_play": True,
        "turnovers": False,
    },
)
```

## Design Principles

-   Football-agnostic utility
-   Pure transformation layer
-   No weighting
-   No ranking
-   No prediction logic

## Validation

Current milestone: - Ruff passes - 66 automated tests pass

## Next Module

`team.py` will combine normalized metrics into: - Offensive Rating -
Defensive Rating - Discipline Rating - Overall Team Rating
