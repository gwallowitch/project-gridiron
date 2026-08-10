# ADR-013: QB Experiment Wiring

QB context is experimental only. The experiment runner now applies:

`rating_difference + rest_advantage * rest_weight + qb_rating_difference * qb_weight`

The QB grid holds rest weight at 0.20 and tests QB weights 0.00, 0.25, 0.50,
0.75, and 1.00. Production prediction behavior is unchanged.

Header-only QB data produces zero differences, so meaningful evaluation waits
for historical starter/rating population in 62C.
