# Step 86B — Explosive-Play Historical Validation

This report validates coverage, dispersion, bounds, and leakage safety. It does not claim predictive value.

## Coverage

| Season | Rows | Week1 unknown | Week2+ both-known | Pass cov | Rush cov | Overall cov |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 | 284 | yes | 100.0% | 94.4% | 94.4% | 94.4% |
| 2023 | 285 | yes | 100.0% | 94.4% | 94.4% | 94.4% |
| 2024 | 285 | yes | 100.0% | 94.4% | 94.4% | 94.4% |
| 2025 | 285 | yes | 100.0% | 94.4% | 94.4% | 94.4% |

## Leakage contract

Step 86A uses completed prior games only. Current-game explosive plays must not contribute to that game's pregame features.

Week 1 is intentionally unknown. From Week 2 onward, prior-game explosive-play history is permitted.

## Gate

**PASS** — the explosive-play family is technically researchable.
