# ADR-098 — Environment Robustness and Prediction-Time Contract

Step 82D strengthened the historical case for weather, but not enough for
promotion.

`adverse_075` had the best aggregate score in 82D, while `adverse_050`,
`adverse_065`, `high_wind_050`, and `high_wind_075` all showed varying degrees
of season consistency. Step 82E keeps those contenders and performs
leave-one-season-out robustness validation.

Candidate selection favors stability: all LOOSO splits improving over baseline
is stronger evidence than simply choosing the lowest four-season aggregate.

Separately, Step 82E formalizes the production constraint. Observed historical
weather is not a valid substitute for weather known at prediction time.
Therefore even a PROVISIONAL_PASS is explicitly not production-eligible.
