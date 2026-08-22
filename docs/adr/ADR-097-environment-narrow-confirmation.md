# ADR-097 — Environment Narrow Confirmation

Step 82C produced a small but unusually consistent historical environment
signal. `adverse_050` ranked first across 2022–2025 with a -0.0003 mean score
delta, 4-0 season record, confidence interval excluding zero, and +0.1% mean
accuracy delta. The promotion review remained INCONCLUSIVE because the average
improvement did not clear the practical threshold.

`high_wind_050` ranked second and was also 4-0, making it a useful related
challenger.

Step 82D therefore tests adverse-weather weights 0.25, 0.35, 0.50, 0.65, 0.75
and high-wind challengers 0.25, 0.50, 0.75. Indoor and extreme-cold families
are parked.

The promoted six-weight model remains frozen, rejected travel weights remain
zero, and observed historical weather is still research-only. Even a strong
82D result cannot be promoted to live use until a prediction-time weather
contract is validated.
