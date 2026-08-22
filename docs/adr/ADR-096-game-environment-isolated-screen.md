# ADR-096 — Isolated Historical Game-Environment Screen

82B passed, but temperature/wind coverage is incomplete in older seasons.
82C therefore neutralizes missing observations instead of treating missing
weather as normal weather.

Four isolated families are tested: adverse weather, indoor/closed roof, high
wind, and extreme cold. Each is screened in both directions at -0.25, -0.10,
+0.10, and +0.25.

The promoted six-weight baseline is frozen and travel weights remain zero.
Observed historical weather is research-only; no environment signal can be
promoted to live use until a prediction-time weather contract is validated.
