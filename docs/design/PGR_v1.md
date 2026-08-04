# Project Gridiron Rating (PGR) v1

## Definition

PGR v1 estimates weekly team strength on a neutral field using only information
available through that week. It combines cumulative performance with a
leak-free schedule adjustment.

## Inputs

- Weekly team ratings
- Strength-of-schedule ratings

## Formula

```text
schedule_adjustment = 0.50 × (strength_of_schedule_rating − 100)
pgr_rating = performance_rating + schedule_adjustment
```

## Output

- `season`
- `week`
- `team`
- `games_played`
- `performance_rating`
- `strength_of_schedule_rating`
- `schedule_adjustment`
- `pgr_rating`
- `model_version`

## Interpretation

- 100 represents an average NFL team.
- Values above 100 indicate above-average estimated strength.
- Values below 100 indicate below-average estimated strength.
- The rating is not yet calibrated to points or win probability.

## Limitations

PGR v1 is intentionally simple. The coefficient has not yet been optimized,
and the model does not account for injuries, home-field advantage, travel,
rest, or recency. Those features should only be added after a benchmarking
framework demonstrates measurable improvement.
