# ADR-063: Long-Field Avoidance Provisional Lock

## Status
Accepted as a provisional research lock.

## Evidence
Step 74D found `long_field_avoidance_weight = 1.00` as the best broad-search
candidate. Step 74E then confirmed the result in a focused search.

At weight 1.00:
- aggregate selection score: 0.4668;
- prior baseline: 0.4672;
- mean paired delta: -0.0004;
- season record: 4-0-0;
- 95% confidence interval: [-0.0008, -0.0001];
- mean winner-accuracy delta: +0.3 percentage points.

The improvement is consistent and statistically directional, but it remains
below the project's practical-improvement threshold. Therefore it is not treated
as an unconditional production promotion.

## Decision
Adopt a provisional research lock:

- `rest_weight = 0.20`
- `off_sack_weight = 10.0`
- `punt_return_weight = 0.24`
- `long_field_avoidance_weight = 1.00`

Future feature research should use this locked candidate as the stronger
comparison point, while retaining a zero-long-field baseline in the 74F
two-config verification grid.

## Parked field-position components
The following remain zero:
- offensive start field position;
- defensive field position;
- short-field rate;
- hidden-yards composite.

## Rationale
The long-field-avoidance signal is:
1. directionally favorable in all four seasons;
2. stable through fine tuning;
3. additive to the three previously retained weights;
4. small enough that its provisional status must remain explicit.
